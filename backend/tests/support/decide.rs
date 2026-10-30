//! The corpus replay's decider: one canonical answer per recorded case, formatted exactly as the Python Store's
//! answers were recorded when the seeded differential ran (ADR-0123 R3).

use std::{
    ffi::OsStr,
    fs,
    net::{IpAddr, Ipv4Addr, Ipv6Addr},
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    sync::Arc,
};

use base64::{Engine as _, engine::general_purpose::STANDARD};
use http::{HeaderMap, HeaderValue};
use store_backend::{
    catalog::project::project,
    clock::ManualClock,
    oauth::{
        broker::CallbackMode, lease::LeaseSigner, neuron::consent, routes::exact_query,
        shape::Scopes,
    },
    query::parse_qsl,
    ratelimit::{ClientKey, Network, client_key, trusted_proxies},
    security::request_id,
    static_files::{
        Site,
        headers::{entity_tag, last_modified, media_type},
    },
};
use strict_json::{Number, Value};
use team_protocol::python::json::{Options, dumps};

const ASCII: Options = Options {
    ensure_ascii: true,
    sort_keys: false,
    compact: true,
};

/// The shared environment: the served build and the two lease keys.
pub struct Decider {
    site: Site,
    keys: [PathBuf; 2],
}

impl Decider {
    /// The decider over the build at `work/build`, with its own lease keys under `work`.
    pub fn new(work: &Path) -> Self {
        let keys = work.join(format!("rust-keys-{}", std::process::id()));
        fs::create_dir_all(&keys).unwrap();
        let install = |name: &str, key: &[u8]| {
            let path = keys.join(name);
            if !path.exists() {
                fs::write(&path, key).unwrap();
                fs::set_permissions(&path, fs::Permissions::from_mode(0o400)).unwrap();
            }
            path
        };
        Self {
            site: Site::new(work.join("build")),
            keys: [
                install("lease-key", &[b'n'; 32]),
                install("lease-key-previous", &[b'q'; 32]),
            ],
        }
    }

    /// The canonical answer to one case.
    pub fn decide(&self, case: &Value) -> String {
        match text(case.get("domain").unwrap()) {
            "query" => query(text(case.get("query").unwrap())),
            "authorization" => authorization(case),
            "lease" => self.lease(case),
            "catalog" => catalog(case),
            "path" => self.path(case),
            "client_key" => client(case),
            "request_id" => identifier(case),
            "media" => media(case),
            other => panic!("unknown domain {other}"),
        }
    }

    fn lease(&self, case: &Value) -> String {
        let scopes = match case.get("scopes").unwrap() {
            Value::Null => None,
            listed => match Scopes::sorted(&strings(listed)) {
                Ok(scopes) => Some(scopes.joined()),
                Err(_) => return "refuse".to_owned(),
            },
        };
        let now = u64::try_from(integer(case.get("now").unwrap())).unwrap();
        let signer = LeaseSigner::new(self.keys.clone(), Arc::new(ManualClock::at(now)));
        let lease = text(case.get("lease").unwrap());
        let token = text(case.get("token").unwrap());
        verdict(signer.verify(lease, token, scopes.as_deref()).is_ok())
    }

    fn path(&self, case: &Value) -> String {
        let navigation = matches!(case.get("navigation"), Some(Value::Bool(true)));
        let reply = self.site.reply(text(case.get("path").unwrap()), navigation);
        let cache = reply
            .header(&http::header::CACHE_CONTROL)
            .map(|value| value.to_str().unwrap().to_owned())
            .unwrap();
        let body = String::from_utf8(reply.body.to_vec()).unwrap();
        json(&Value::Array(vec![
            Value::Number(Number::Int(i64::from(reply.status.as_u16()))),
            Value::String(cache),
            Value::String(body),
        ]))
    }
}

fn text(value: &Value) -> &str {
    match value {
        Value::String(text) => text,
        other => panic!("not a string: {other:?}"),
    }
}

fn strings(value: &Value) -> Vec<&str> {
    match value {
        Value::Array(items) => items.iter().map(text).collect(),
        other => panic!("not an array: {other:?}"),
    }
}

fn integer(value: &Value) -> i128 {
    match value {
        Value::Number(Number::Int(number)) => i128::from(*number),
        Value::Number(Number::BigInt(digits)) => digits.parse().unwrap(),
        other => panic!("not an integer: {other:?}"),
    }
}

fn json(value: &Value) -> String {
    dumps(value, ASCII)
}

fn verdict(ok: bool) -> String {
    if ok { "ok" } else { "refuse" }.to_owned()
}

fn pairs(parsed: &[(String, String)]) -> Value {
    Value::Array(
        parsed
            .iter()
            .map(|(name, value)| {
                Value::Array(vec![
                    Value::String(name.clone()),
                    Value::String(value.clone()),
                ])
            })
            .collect(),
    )
}

fn values(fields: Option<Vec<String>>) -> Value {
    fields.map_or(Value::Null, |fields| {
        Value::Array(fields.into_iter().map(Value::String).collect())
    })
}

fn query(text: &str) -> String {
    let lenient = parse_qsl(text, false, None).unwrap();
    let strict = parse_qsl(text, true, Some(7)).ok();
    let start = exact_query(
        Some(text),
        &["state", "code_challenge", "scope", "callback"],
    )
    .filter(|fields| CallbackMode::parse(&fields[3]).is_some());
    let callback = exact_query(Some(text), &["state", "code", "scope"]);
    json(&Value::Array(vec![
        pairs(&lenient),
        strict.as_deref().map_or(Value::Null, pairs),
        values(start),
        values(callback),
    ]))
}

fn authorization(case: &Value) -> String {
    let Ok(scopes) = Scopes::sorted(&strings(case.get("scopes").unwrap())) else {
        return "refuse".to_owned();
    };
    let reply = Value::Object(vec![(
        "authorization_url".to_owned(),
        case.get("url").unwrap().clone(),
    )]);
    let state = text(case.get("state").unwrap());
    let challenge = text(case.get("challenge").unwrap());
    verdict(consent(&reply, state, challenge, &scopes).is_ok())
}

fn catalog(case: &Value) -> String {
    let document = STANDARD
        .decode(text(case.get("document").unwrap()))
        .unwrap();
    strict_json::parse(&document)
        .ok()
        .and_then(|value| project(&value, text(case.get("locale").unwrap())))
        .map_or_else(
            || "refuse".to_owned(),
            |bytes| String::from_utf8(bytes).unwrap(),
        )
}

fn network(network: Network) -> Value {
    Value::String(match network {
        Network::V4(address, length) => format!("{}/{length}", Ipv4Addr::from(address)),
        Network::V6(address, length) => format!("{}/{length}", Ipv6Addr::from(address)),
    })
}

fn client(case: &Value) -> String {
    let proxies = match case.get("proxies").unwrap() {
        Value::Null => trusted_proxies(None),
        value => trusted_proxies(Some(OsStr::new(text(value)))),
    };
    let Ok(proxies) = proxies else {
        return json(&Value::Array(vec![
            Value::String("refuse".to_owned()),
            Value::Null,
        ]));
    };
    let mut headers = HeaderMap::new();
    for value in strings(case.get("forwarded").unwrap()) {
        headers.append("cf-connecting-ip", HeaderValue::from_str(value).unwrap());
    }
    let peer: IpAddr = text(case.get("peer").unwrap()).parse().unwrap();
    let key = match client_key(peer, &headers, &proxies) {
        Ok(ClientKey::V4(address)) => Ipv4Addr::from(address).to_string(),
        Ok(ClientKey::V6Prefix(prefix)) => {
            format!("{}/64", Ipv6Addr::from(u128::from(prefix) << 64))
        }
        Err(_) => "refuse".to_owned(),
    };
    json(&Value::Array(vec![
        Value::Array(proxies.into_iter().map(network).collect()),
        Value::String(key),
    ]))
}

fn identifier(case: &Value) -> String {
    let mut headers = HeaderMap::new();
    for value in strings(case.get("values").unwrap()) {
        let latin1: Vec<u8> = value
            .chars()
            .map(|character| u8::try_from(u32::from(character)).unwrap())
            .collect();
        headers.append("x-request-id", HeaderValue::from_bytes(&latin1).unwrap());
    }
    let first = request_id(&headers);
    if first == request_id(&headers) {
        first
    } else {
        "fresh".to_owned()
    }
}

fn media(case: &Value) -> String {
    let mtime = integer(case.get("mtime_ns").unwrap());
    let size = u64::try_from(integer(case.get("size").unwrap())).unwrap();
    json(&Value::Array(vec![
        Value::String(media_type(text(case.get("name").unwrap())).to_owned()),
        Value::String(entity_tag(mtime, size)),
        last_modified(mtime).map_or(Value::Null, Value::String),
    ]))
}
