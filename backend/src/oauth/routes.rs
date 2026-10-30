//! The broker's five routes. Each checks what the Python routes checked before the executor, then runs the broker
//! operation as an owned task within the capacity ([`super::admission`]): the start route first counts the start
//! against its client ([`crate::ratelimit`]).

use std::{net::IpAddr, sync::Arc};

use http::{HeaderMap, HeaderValue, StatusCode, header};
use strict_json::{Number, Value};
use team_protocol::python::json::{Options, dumps};

use super::{
    PRIVATE_NO_STORE,
    admission::{Capacity, Operation, capacity_reached},
    body::{Body, admitted, member, text},
    broker::{Broker, CallbackMode, Completion, Handoff, nonce},
    completion::completion_page,
    failure,
    shape::Scopes,
};
use crate::{
    query::parse_qsl,
    ratelimit::{StartLimit, StartRefusal},
    response::Reply,
    security::internal_error,
};

const JSON_COMPACT: Options = Options {
    ensure_ascii: false,
    sort_keys: false,
    compact: true,
};

/// One server-only broker operation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Post {
    /// `POST /api/oauth/cloudflare/claim`.
    Claim,
    /// `POST /api/oauth/cloudflare/refresh`.
    Refresh,
    /// `POST /api/oauth/cloudflare/revoke`.
    Revoke,
}

impl Post {
    const fn name(self) -> &'static str {
        match self {
            Self::Claim => "claim",
            Self::Refresh => "refresh",
            Self::Revoke => "revoke",
        }
    }

    const fn fields(self) -> &'static [&'static str] {
        match self {
            Self::Claim => &["claim", "state", "code_verifier"],
            Self::Refresh => &["refresh_token", "broker_lease", "scopes"],
            Self::Revoke => &["token", "broker_lease"],
        }
    }
}

/// The broker, its capacity, and the start limit.
pub struct Oauth {
    broker: Arc<Broker>,
    capacity: Capacity,
    start_limit: StartLimit,
}

impl Oauth {
    /// The routes over this broker and start limit.
    #[must_use]
    pub fn new(broker: Broker, start_limit: StartLimit) -> Self {
        Self {
            broker: Arc::new(broker),
            capacity: Capacity::new(),
            start_limit,
        }
    }

    /// Count one start from `peer` against its client: `None` when admitted, otherwise the refusal.
    #[must_use]
    pub fn admit_start(&self, peer: IpAddr, headers: &HeaderMap) -> Option<Reply> {
        let refusal = self.start_limit.admit(peer, headers).err()?;
        let (status, extra) = match refusal {
            StartRefusal::ClientAddress => (StatusCode::BAD_REQUEST, None),
            StartRefusal::Limited(seconds) => (
                StatusCode::TOO_MANY_REQUESTS,
                Some((header::RETRY_AFTER, HeaderValue::from(seconds))),
            ),
        };
        Some(failure("start", status, extra))
    }

    /// `GET /api/oauth/cloudflare/start`: exactly `state`, `code_challenge`, `scope`, and a known `callback`.
    pub async fn start(
        &self,
        peer: IpAddr,
        headers: &HeaderMap,
        query: Option<&str>,
        path: &str,
    ) -> Reply {
        if let Some(refused) = self.admit_start(peer, headers) {
            return refused;
        }
        let Some(fields) = exact_query(query, &["state", "code_challenge", "scope", "callback"])
        else {
            return failure("start", StatusCode::BAD_REQUEST, None);
        };
        let Some(mode) = CallbackMode::parse(&fields[3]) else {
            return failure("start", StatusCode::BAD_REQUEST, None);
        };
        let broker = Arc::clone(&self.broker);
        self.owned(
            path,
            Box::pin(async move {
                let scopes: Vec<&str> = fields[2].split(' ').collect();
                match broker.start(&fields[0], &fields[1], mode, &scopes).await {
                    Ok(location) => redirect(&location),
                    Err(_) => failure("start", StatusCode::BAD_GATEWAY, None),
                }
            }),
        )
        .await
    }

    /// `GET /api/oauth/cloudflare/callback`: exactly `state`, `code`, and `scope`.
    pub async fn callback(&self, query: Option<&str>, path: &str) -> Reply {
        let Some(fields) = exact_query(query, &["state", "code", "scope"]) else {
            return failure("callback", StatusCode::BAD_REQUEST, None);
        };
        let broker = Arc::clone(&self.broker);
        self.owned(
            path,
            Box::pin(async move {
                let scopes: Vec<&str> = fields[2].split(' ').collect();
                match broker.callback(&fields[0], &fields[1], &scopes).await {
                    Ok(Completion::Redirect(location)) => redirect(&location),
                    Ok(Completion::OutOfBand(code)) => completion_page(&code, &nonce()),
                    Err(_) => failure("callback", StatusCode::BAD_GATEWAY, None),
                }
            }),
        )
        .await
    }

    /// A server-only operation: an exact JSON body, then the broker.
    pub async fn post(
        &self,
        operation: Post,
        headers: &HeaderMap,
        body: Body,
        path: &str,
    ) -> Reply {
        let members = match admitted(headers, body, operation.fields()).await {
            Ok(members) => members,
            Err(status) => return failure(operation.name(), status, None),
        };
        let broker = Arc::clone(&self.broker);
        self.owned(
            path,
            Box::pin(async move {
                match act(&broker, operation, &members).await {
                    Some(body) => Reply::json(
                        StatusCode::OK,
                        body,
                        vec![(header::CACHE_CONTROL, PRIVATE_NO_STORE)],
                    ),
                    None => failure(operation.name(), StatusCode::BAD_GATEWAY, None),
                }
            }),
        )
        .await
    }

    /// Run `operation` as an owned task within the capacity, or refuse it past the capacity.
    async fn owned(&self, path: &str, operation: Operation) -> Reply {
        let Some(admitted) = self.capacity.admit() else {
            return capacity_reached(path);
        };
        admitted
            .spawn(operation)
            .await
            .unwrap_or_else(|_| internal_error(path))
    }

    /// Wait until every owned operation has ended, admitting no other.
    pub async fn drained(&self) {
        self.capacity.drained().await;
    }

    /// Whether the broker holds no state.
    #[cfg(test)]
    pub(crate) fn idle(&self) -> bool {
        self.broker.idle()
    }

    /// Abort every owned operation; its guards restore the broker's state.
    pub fn abort(&self) {
        self.capacity.abort();
    }
}

/// The query's values for exactly these names, each once, in this order.
fn exact_query(query: Option<&str>, names: &[&str]) -> Option<Vec<String>> {
    let pairs = parse_qsl(query.unwrap_or_default(), false, None).ok()?;
    let mut values = Vec::with_capacity(names.len());
    for name in names {
        let mut matching = pairs.iter().filter(|(key, _)| key == name);
        let (Some((_, value)), None) = (matching.next(), matching.next()) else {
            return None;
        };
        values.push(value.clone());
    }
    (pairs.len() == names.len()).then_some(values)
}

/// The 303 that sends the browser on, never cached and without a referrer.
fn redirect(location: &str) -> Reply {
    Reply::redirect(
        StatusCode::SEE_OTHER,
        HeaderValue::from_str(location).expect("a broker location holds only URL characters"),
        vec![
            (header::CACHE_CONTROL, PRIVATE_NO_STORE),
            (
                header::REFERRER_POLICY,
                HeaderValue::from_static("no-referrer"),
            ),
        ],
    )
}

/// The broker call of a server-only operation and its JSON reply, or `None` when the broker refuses it.
async fn act(broker: &Broker, operation: Post, members: &[(String, Value)]) -> Option<String> {
    let field = |name: &str| text(members, name);
    let handoff = match operation {
        Post::Claim => broker.claim(field("claim")?, field("state")?, field("code_verifier")?),
        Post::Refresh => {
            let scopes = Scopes::from_json(member(members, "scopes")?).ok()?;
            broker
                .refresh(field("refresh_token")?, field("broker_lease")?, &scopes)
                .await
        }
        Post::Revoke => {
            broker
                .revoke(field("token")?, field("broker_lease")?)
                .await
                .ok()?;
            return Some(String::from("{\"revoked\":true}"));
        }
    };
    handoff.ok().map(|handoff| payload(&handoff))
}

/// `{"access_token","refresh_token","expires_in","scopes","broker_lease"}` in that order, compact.
fn payload(handoff: &Handoff) -> String {
    let text = |value: &str| Value::String(value.to_owned());
    let scopes = handoff
        .scopes
        .names()
        .iter()
        .map(|scope| text(scope))
        .collect();
    let members = vec![
        ("access_token".to_owned(), text(&handoff.tokens.access)),
        ("refresh_token".to_owned(), text(&handoff.tokens.refresh)),
        (
            "expires_in".to_owned(),
            Value::Number(Number::Int(handoff.tokens.expires_in)),
        ),
        ("scopes".to_owned(), Value::Array(scopes)),
        ("broker_lease".to_owned(), text(&handoff.lease)),
    ];
    dumps(&Value::Object(members), JSON_COMPACT)
}

#[cfg(test)]
mod tests;
