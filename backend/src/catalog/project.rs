//! The strict projection of Developers' public catalog into the browser's, in one interface language (ADR-0091),
//! rule for rule as the Python Store's `catalog.py`: every field set closed, every text bounded in code points,
//! trimmed as Python's `strip()` trims, free of control characters, and (for localized copy) printable and NFC.
//! Any other value refuses the whole catalog.

use std::{collections::HashSet, sync::LazyLock};

use strict_json::{Number, Value};
use team_protocol::{
    identifiers::{canonical_assistant_id, canonical_identifier},
    payload::{
        ASSISTANT_VERSION_RE, CHAT_LOCALES, DETAILS_CREATOR_RE, GITHUB_REPOSITORY_RE,
        MAX_DETAILS_CREATORS, SOURCE_DIGEST_RE, canonical_creator_links, canonical_help_url,
    },
    python::{
        json::{CANONICAL, dumps},
        regex::{Pattern, declared},
        text,
        value::{array, exact_object, field, string},
    },
};

/// The most Assistants one catalog lists.
pub const MAX_ASSISTANTS: usize = 1_000;
/// The most Actions one Assistant declares, as Developers, Team, and the Brain admit.
const MAX_ACTIONS: usize = 128;
const HUMAN_REQUEST_KINDS: [&str; 11] = [
    "approval",
    "input:text",
    "input:textarea",
    "input:password",
    "input:phone",
    "input:select",
    "input:choice",
    "input:choices",
    "auth:password",
    "auth:totp",
    "auth:passkey",
];
/// The kinds of which one Action may request at most one.
const GATE_KINDS: [&str; 4] = ["approval", "auth:password", "auth:totp", "auth:passkey"];
const ASSISTANT_FIELDS: [&str; 15] = [
    "assistant_id",
    "name",
    "summary",
    "description",
    "links",
    "assistant_version",
    "creators",
    "github",
    "icon_digest",
    "source_digest",
    "platforms",
    "allowed_hosts",
    "integrations",
    "stored_inputs",
    "actions",
];
const ACTION_FIELDS: [&str; 6] = [
    "id",
    "integrations",
    "stored_inputs",
    "human_requests",
    "effect",
    "description",
];
const STORED_INPUT_FIELDS: [&str; 5] = ["id", "kind", "label", "description", "help_url"];
const DESCRIPTION_BOUND: usize = 500;
const LINE_BOUND: usize = 120;
const NAME_BOUND: usize = 80;
/// Developers' public host shape: lowercase DNS labels under an alphabetic top-level label.
static ALLOWED_HOST_RE: LazyLock<Pattern> = LazyLock::new(|| {
    declared(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?")
});
/// Developers' Integration scope grammar.
static INTEGRATION_SCOPE_RE: LazyLock<Pattern> =
    LazyLock::new(|| declared(r"[a-z0-9][a-z0-9.:/_-]*"));

/// The browser catalog bytes of Developers' catalog for exactly `locale`, or `None` when Store refuses it.
///
/// The bytes are `json.dumps(projected, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
#[must_use]
pub fn project(value: &Value, locale: &str) -> Option<Vec<u8>> {
    let members = exact_object(value, &["version", "locale", "assistants"])?;
    let version = matches!(field(members, "version"), Value::Number(Number::Int(1)));
    let same_locale =
        string(field(members, "locale")) == Some(locale) && CHAT_LOCALES.contains(&locale);
    if !version || !same_locale {
        return None;
    }
    let items =
        array(field(members, "assistants")).filter(|items| items.len() <= MAX_ASSISTANTS)?;
    let assistants = items.iter().map(assistant).collect::<Option<Vec<_>>>()?;
    let identities: Vec<&str> = assistants.iter().map(|(id, _)| id.as_str()).collect();
    if !identities.windows(2).all(|pair| pair[0] < pair[1]) {
        return None;
    }
    let projected = Value::Object(vec![
        ("version".to_owned(), Value::Number(Number::Int(1))),
        ("locale".to_owned(), Value::String(locale.to_owned())),
        (
            "assistants".to_owned(),
            Value::Array(assistants.into_iter().map(|(_, value)| value).collect()),
        ),
    ]);
    Some(dumps(&projected, CANONICAL).into_bytes())
}

fn text_value(text: &str) -> Value {
    Value::String(text.to_owned())
}

fn strings(items: &[&str]) -> Value {
    Value::Array(items.iter().map(|item| text_value(item)).collect())
}

fn object(members: Vec<(&str, Value)>) -> Value {
    Value::Object(
        members
            .into_iter()
            .map(|(name, value)| (name.to_owned(), value))
            .collect(),
    )
}

/// One bounded, trimmed, control-free line of display text.
fn line(value: &Value, maximum: usize) -> Option<&str> {
    let line = string(value)?;
    let bounded = (1..=maximum).contains(&text::len(line));
    let controlled = line
        .chars()
        .any(|character| character < ' ' || character == '\u{7f}');
    (bounded && text::strip(line) == line && !controlled).then_some(line)
}

/// One localized display text: a [`line`] that is also printable and NFC.
fn display(value: &Value, maximum: usize) -> Option<&str> {
    line(value, maximum).filter(|line| text::isprintable(line) && text::is_nfc(line))
}

/// A list of at most `maximum` distinct strings of 1 to `item_maximum` code points.
fn closed_strings(value: &Value, maximum: usize, item_maximum: usize) -> Option<Vec<&str>> {
    let items = array(value).filter(|items| items.len() <= maximum)?;
    let strings = items
        .iter()
        .map(|item| string(item).filter(|text| (1..=item_maximum).contains(&text::len(text))))
        .collect::<Option<Vec<_>>>()?;
    let distinct: HashSet<&str> = strings.iter().copied().collect();
    (distinct.len() == strings.len()).then_some(strings)
}

fn assistant(value: &Value) -> Option<(String, Value)> {
    let members = exact_object(value, &ASSISTANT_FIELDS)?;
    let id = canonical_assistant_id(field(members, "assistant_id"))?;
    let version = string(field(members, "assistant_version"))
        .filter(|version| ASSISTANT_VERSION_RE.is_full(version))?;
    let source = string(field(members, "source_digest"))
        .filter(|digest| SOURCE_DIGEST_RE.is_full(digest))?;
    let icon =
        string(field(members, "icon_digest")).filter(|digest| SOURCE_DIGEST_RE.is_full(digest))?;
    let platforms = field(members, "platforms");
    let github =
        string(field(members, "github")).filter(|github| GITHUB_REPOSITORY_RE.is_full(github))?;
    if *platforms != strings(&["linux/amd64", "linux/arm64"]) {
        return None;
    }
    let (stored_inputs, stored_ids) = stored_inputs(field(members, "stored_inputs"))?;
    let projected = object(vec![
        ("assistant_id", text_value(id)),
        (
            "name",
            text_value(line(field(members, "name"), NAME_BOUND)?),
        ),
        (
            "summary",
            text_value(line(field(members, "summary"), NAME_BOUND)?),
        ),
        (
            "description",
            text_value(display(field(members, "description"), DESCRIPTION_BOUND)?),
        ),
        ("links", canonical_creator_links(field(members, "links"))?),
        ("assistant_version", text_value(version)),
        ("creators", strings(&creators(field(members, "creators"))?)),
        ("github", text_value(github)),
        ("source_digest", text_value(source)),
        ("icon_digest", text_value(icon)),
        ("platforms", platforms.clone()),
        (
            "allowed_hosts",
            strings(&allowed_hosts(field(members, "allowed_hosts"))?),
        ),
        (
            "integrations",
            integrations(field(members, "integrations"))?,
        ),
        ("stored_inputs", stored_inputs),
        ("actions", actions(field(members, "actions"), &stored_ids)?),
    ]);
    Some((id.to_owned(), projected))
}

fn creators(value: &Value) -> Option<Vec<&str>> {
    closed_strings(value, MAX_DETAILS_CREATORS, 39).filter(|creators| {
        !creators.is_empty()
            && creators
                .iter()
                .all(|creator| DETAILS_CREATOR_RE.is_full(creator))
    })
}

fn allowed_hosts(value: &Value) -> Option<Vec<&str>> {
    closed_strings(value, 32, 253)
        .filter(|hosts| hosts.iter().all(|host| ALLOWED_HOST_RE.is_full(host)))
}

fn integrations(value: &Value) -> Option<Value> {
    let items = array(value).filter(|items| items.len() <= 16)?;
    let mut projected = Vec::with_capacity(items.len());
    let mut identities = Vec::with_capacity(items.len());
    for item in items {
        let members = exact_object(item, &["id", "provider", "scopes"])?;
        let scopes = closed_strings(field(members, "scopes"), 32, 128).filter(|scopes| {
            !scopes.is_empty()
                && scopes
                    .iter()
                    .all(|scope| INTEGRATION_SCOPE_RE.is_full(scope))
        })?;
        let id = canonical_identifier(field(members, "id"))?;
        if field(members, "provider") != field(members, "id") {
            return None;
        }
        identities.push(id);
        projected.push(object(vec![
            ("id", text_value(id)),
            ("provider", text_value(id)),
            ("scopes", strings(&scopes)),
        ]));
    }
    identities
        .windows(2)
        .all(|pair| pair[0] < pair[1])
        .then_some(Value::Array(projected))
}

fn stored_inputs(value: &Value) -> Option<(Value, Vec<&str>)> {
    let items = array(value).filter(|items| items.len() <= 8)?;
    let mut projected = Vec::with_capacity(items.len());
    let mut identities = Vec::with_capacity(items.len());
    for item in items {
        let members = exact_object(item, &STORED_INPUT_FIELDS)?;
        let id = canonical_identifier(field(members, "id"))?;
        let help_url = canonical_help_url(field(members, "help_url"))?;
        if string(field(members, "kind")) != Some("password") {
            return None;
        }
        projected.push(object(vec![
            ("id", text_value(id)),
            (
                "label",
                text_value(display(field(members, "label"), LINE_BOUND)?),
            ),
            (
                "description",
                text_value(display(field(members, "description"), DESCRIPTION_BOUND)?),
            ),
            ("help_url", text_value(help_url)),
        ]));
        identities.push(id);
    }
    let distinct: HashSet<&str> = identities.iter().copied().collect();
    (distinct.len() == identities.len()).then_some((Value::Array(projected), identities))
}

fn actions(value: &Value, stored: &[&str]) -> Option<Value> {
    let items = array(value).filter(|items| (1..=MAX_ACTIONS).contains(&items.len()))?;
    let projected = items
        .iter()
        .map(|item| action(item, stored))
        .collect::<Option<Vec<_>>>()?;
    let identities: HashSet<&str> = projected.iter().map(|(id, _)| *id).collect();
    (identities.len() == projected.len())
        .then(|| Value::Array(projected.into_iter().map(|(_, value)| value).collect()))
}

fn action<'a>(item: &'a Value, stored: &[&str]) -> Option<(&'a str, Value)> {
    let members = exact_object(item, &ACTION_FIELDS)?;
    let id = canonical_identifier(field(members, "id"))?;
    let effect = string(field(members, "effect"))
        .filter(|effect| matches!(*effect, "read_only" | "mutating"))?;
    let requests = closed_strings(field(members, "human_requests"), 8, 25).filter(|requests| {
        requests
            .iter()
            .all(|kind| HUMAN_REQUEST_KINDS.contains(kind))
            && requests
                .iter()
                .filter(|kind| GATE_KINDS.contains(kind))
                .count()
                <= 1
    })?;
    let integrations =
        closed_strings(field(members, "integrations"), 4, 64).filter(|identifiers| {
            identifiers
                .iter()
                .all(|identifier| canonical_identifier(&text_value(identifier)).is_some())
        })?;
    closed_strings(field(members, "stored_inputs"), 8, 64)
        .filter(|used| used.iter().all(|id| stored.contains(id)))?;
    let projected = object(vec![
        ("id", text_value(id)),
        ("integrations", strings(&integrations)),
        ("human_requests", strings(&requests)),
        ("effect", text_value(effect)),
        (
            "description",
            text_value(display(field(members, "description"), LINE_BOUND)?),
        ),
    ]);
    Some((id, projected))
}

#[cfg(test)]
mod tests;
