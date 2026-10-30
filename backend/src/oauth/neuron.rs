//! The Neuron OAuth client: the Access service token Store holds, never the OAuth client secret.
//!
//! Each call reads the Access credential, opens a tunnel ([`super::tunnel`]), and posts one compact ASCII JSON body
//! to `/api/internal/oauth/cloudflare/{operation}` with the Python broker's header set. Neuron must answer 200 with a
//! JSON media type and a strict JSON object of at most 32 KiB, whose members each operation then checks exactly.

use std::path::PathBuf;

use bytes::Bytes;
use http::{Request, StatusCode, header};
use http_body_util::{BodyExt, Full, Limited};
use hyper::client::conn::http1;
use hyper_util::rt::TokioIo;
use strict_json::{Number, Value};
use team_protocol::python::json::{Options, dumps};
use zeroize::Zeroizing;

use super::{
    BrokerError,
    secret::{ACCESS_CLIENT_ID_PATH, ACCESS_CLIENT_SECRET_PATH, access_credential},
    shape::{Scopes, code, token},
    tunnel::{NEURON_HOST, Tunnel},
};
use crate::query::parse_qsl;

/// The largest Neuron reply body.
pub const MAX_RESPONSE_BYTES: usize = 32 * 1024;
/// Cloudflare's consent entrance every authorization URL starts with.
pub const AUTHORIZATION_PREFIX: &str = "https://dash.cloudflare.com/oauth2/auth?";
/// The platform callback Cloudflare returns the browser to.
pub const PLATFORM_CALLBACK: &str = "https://shimpz.com/api/oauth/cloudflare/callback";
const MAX_AUTHORIZATION_URL_CHARS: usize = 4096;
const MIN_TOKEN_SECONDS: i64 = 30;
const MAX_TOKEN_SECONDS: i64 = 31_536_000;
const ASCII_COMPACT: Options = Options {
    ensure_ascii: true,
    sort_keys: false,
    compact: true,
};

/// The tokens one exchange or refresh returned.
pub struct Tokens {
    /// The access token.
    pub access: Zeroizing<String>,
    /// The refresh token.
    pub refresh: Zeroizing<String>,
    /// Seconds until the access token expires.
    pub expires_in: i64,
}

/// One Neuron OAuth operation.
#[derive(Clone, Copy, Debug)]
enum Operation {
    Authorization,
    Exchange,
    Refresh,
    Revoke,
}

impl Operation {
    const fn path(self) -> &'static str {
        match self {
            Self::Authorization => "/api/internal/oauth/cloudflare/authorization",
            Self::Exchange => "/api/internal/oauth/cloudflare/exchange",
            Self::Refresh => "/api/internal/oauth/cloudflare/refresh",
            Self::Revoke => "/api/internal/oauth/cloudflare/revoke",
        }
    }
}

/// Neuron behind the tunnel, with the Access credential's files.
pub struct Neuron {
    tunnel: Tunnel,
    credential: [PathBuf; 2],
}

impl Neuron {
    /// The deployed Store's Neuron client.
    #[must_use]
    pub fn production() -> Self {
        Self::new(
            Tunnel::production(),
            [
                PathBuf::from(ACCESS_CLIENT_ID_PATH),
                PathBuf::from(ACCESS_CLIENT_SECRET_PATH),
            ],
        )
    }

    /// A client reaching Neuron through `tunnel` with the Access client id and secret at these paths.
    #[must_use]
    pub fn new(tunnel: Tunnel, credential: [PathBuf; 2]) -> Self {
        Self { tunnel, credential }
    }

    /// Ask Neuron for Cloudflare's consent URL for this broker state, PKCE challenge, and scopes (T11's grammar).
    ///
    /// # Errors
    ///
    /// The call fails, or the URL is not exactly the consent URL for these values.
    pub async fn authorization(
        &self,
        state: &str,
        challenge: &str,
        scopes: &Scopes,
    ) -> Result<String, BrokerError> {
        let body = body(vec![
            ("state", text(state)),
            ("code_challenge", text(challenge)),
            ("scopes", scope_array(scopes)),
        ]);
        let reply = self.call(Operation::Authorization, body).await?;
        let url = only(&reply, "authorization_url").and_then(|value| match value {
            Value::String(url) => Some(url.as_str()),
            _ => None,
        });
        let url = url.ok_or(BrokerError)?;
        consent_url(url, state, challenge, scopes)?;
        Ok(url.to_owned())
    }

    /// Exchange an authorization code with the broker's PKCE verifier.
    ///
    /// # Errors
    ///
    /// The call fails, or the tokens are not exactly shaped for these scopes.
    pub async fn exchange(
        &self,
        authorization_code: &str,
        verifier: &str,
        scopes: &Scopes,
    ) -> Result<Tokens, BrokerError> {
        let body = body(vec![
            ("code", text(authorization_code)),
            ("code_verifier", text(verifier)),
            ("scopes", scope_array(scopes)),
        ]);
        tokens(&self.call(Operation::Exchange, body).await?, scopes)
    }

    /// Refresh tokens for exactly these scopes.
    ///
    /// # Errors
    ///
    /// The call fails, or the tokens are not exactly shaped for these scopes.
    pub async fn refresh(
        &self,
        refresh_token: &str,
        scopes: &Scopes,
    ) -> Result<Tokens, BrokerError> {
        let body = body(vec![
            ("refresh_token", text(refresh_token)),
            ("scopes", scope_array(scopes)),
        ]);
        tokens(&self.call(Operation::Refresh, body).await?, scopes)
    }

    /// Revoke a token; Neuron must acknowledge with exactly `{"revoked": true}` (T15).
    ///
    /// # Errors
    ///
    /// The call fails, or the acknowledgement is anything else.
    pub async fn revoke(&self, revoked: &str) -> Result<(), BrokerError> {
        let reply = self
            .call(Operation::Revoke, body(vec![("token", text(revoked))]))
            .await?;
        match only(&reply, "revoked") {
            Some(Value::Bool(true)) => Ok(()),
            _ => Err(BrokerError),
        }
    }

    /// Post `body` to the operation's path and return Neuron's JSON object.
    async fn call(&self, operation: Operation, body: String) -> Result<Value, BrokerError> {
        let credential = access_credential(&self.credential[0], &self.credential[1])?;
        let request = Request::post(operation.path())
            .header(header::HOST, NEURON_HOST)
            .header(header::ACCEPT_ENCODING, "identity")
            .header("cf-access-client-id", credential.client_id.as_str())
            .header("cf-access-client-secret", credential.client_secret.as_str())
            .header(header::ACCEPT, "application/json")
            .header(header::CONTENT_TYPE, "application/json")
            .header(header::CONTENT_LENGTH, body.len())
            .header(header::USER_AGENT, "shimpz-oauth-broker/1")
            .body(Full::new(Bytes::from(body)))
            .expect("every Neuron request header is valid");
        let stream = self.tunnel.open().await?;
        let (mut sender, connection) = http1::handshake(TokioIo::new(stream))
            .await
            .or(Err(BrokerError))?;
        tokio::spawn(connection);
        let response = sender.send_request(request).await.or(Err(BrokerError))?;
        let json_reply = response.status() == StatusCode::OK && json_media_type(response.headers());
        let body = Limited::new(response.into_body(), MAX_RESPONSE_BYTES)
            .collect()
            .await
            .or(Err(BrokerError))?
            .to_bytes();
        match strict_json::parse(&body) {
            Ok(value @ Value::Object(_)) if json_reply => Ok(value),
            _ => Err(BrokerError),
        }
    }
}

/// Whether the reply's `Content-Type` values, joined as `http.client` joins them, name `application/json` before
/// any parameter, ignoring case and surrounding space.
fn json_media_type(headers: &http::HeaderMap) -> bool {
    let joined: Vec<String> = headers
        .get_all(header::CONTENT_TYPE)
        .iter()
        .map(|value| {
            value
                .as_bytes()
                .iter()
                .map(|byte| char::from(*byte))
                .collect()
        })
        .collect();
    let joined = joined.join(", ");
    let media_type = joined.split(';').next().unwrap_or_default();
    media_type.trim().to_lowercase() == "application/json"
}

fn text(value: &str) -> Value {
    Value::String(value.to_owned())
}

fn scope_array(scopes: &Scopes) -> Value {
    Value::Array(scopes.names().iter().map(|scope| text(scope)).collect())
}

/// `json.dumps(members, ensure_ascii=True, separators=(",", ":"))` in member order.
fn body(members: Vec<(&str, Value)>) -> String {
    let members = members
        .into_iter()
        .map(|(name, value)| (name.to_owned(), value))
        .collect();
    dumps(&Value::Object(members), ASCII_COMPACT)
}

/// The value of an object whose only member is `name`.
fn only<'a>(object: &'a Value, name: &str) -> Option<&'a Value> {
    match object {
        Value::Object(members) if members.len() == 1 && members[0].0 == name => Some(&members[0].1),
        _ => None,
    }
}

/// T11: at most 4,096 characters a redirect carries unchanged, without a fragment, Cloudflare's consent prefix, and
/// exactly the seven expected query fields.
fn consent_url(
    url: &str,
    state: &str,
    challenge: &str,
    scopes: &Scopes,
) -> Result<(), BrokerError> {
    let alphabet = url
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || b"_.~:/%?=@[]!$&'()*+,;-".contains(&byte));
    let sized = (1..=MAX_AUTHORIZATION_URL_CHARS).contains(&url.len());
    let query = url
        .strip_prefix(AUTHORIZATION_PREFIX)
        .filter(|_| alphabet && sized)
        .ok_or(BrokerError)?;
    let pairs = parse_qsl(query, true, Some(7)).or(Err(BrokerError))?;
    let field = |name: &str| {
        pairs
            .iter()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value.as_str())
    };
    let mut names: Vec<&str> = pairs.iter().map(|(name, _)| name.as_str()).collect();
    names.sort_unstable();
    names.dedup();
    let joined = scopes.joined();
    // At most seven pairs parse, so seven distinct names are exactly seven pairs.
    let exact = names.len() == 7
        && field("response_type") == Some("code")
        && field("redirect_uri") == Some(PLATFORM_CALLBACK)
        && field("state") == Some(state)
        && field("code_challenge") == Some(challenge)
        && field("code_challenge_method") == Some("S256")
        && field("scope") == Some(joined.as_str())
        && field("client_id").is_some_and(|client| code(client, 8, 256));
    exact.then_some(()).ok_or(BrokerError)
}

/// Exactly `access_token`, `refresh_token`, `scopes` equal to the expected, and an integer `expires_in` from 30 s to a
/// year.
fn tokens(reply: &Value, expected: &Scopes) -> Result<Tokens, BrokerError> {
    let Value::Object(members) = reply else {
        return Err(BrokerError);
    };
    let field = |name: &str| {
        members
            .iter()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value)
    };
    let string = |name: &str| match field(name) {
        Some(Value::String(value)) if token(value) => Some(Zeroizing::new(value.clone())),
        _ => None,
    };
    let scopes_match = field("scopes")
        .is_some_and(|value| Scopes::from_json(value).is_ok_and(|scopes| scopes == *expected));
    let expires_in = match field("expires_in") {
        Some(Value::Number(Number::Int(seconds)))
            if (MIN_TOKEN_SECONDS..=MAX_TOKEN_SECONDS).contains(seconds) =>
        {
            Some(*seconds)
        }
        _ => None,
    };
    let (Some(access), Some(refresh), Some(expires_in), true, 4) = (
        string("access_token"),
        string("refresh_token"),
        expires_in,
        scopes_match,
        members.len(),
    ) else {
        return Err(BrokerError);
    };
    Ok(Tokens {
        access,
        refresh,
        expires_in,
    })
}

#[cfg(test)]
mod tests;
