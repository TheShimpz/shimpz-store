//! The projection, rule by rule; the valid catalog's expected bytes are the Python Store's own output for it.

use strict_json::Value;

use super::{MAX_ASSISTANTS, project};

const CATALOG: &str = include_str!("catalog.json");
const PROJECTED: &str = include_str!("projected.json");

fn projected(document: &str, locale: &str) -> Option<String> {
    let value: Value = strict_json::parse(document.as_bytes()).unwrap();
    project(&value, locale).map(|bytes| String::from_utf8(bytes).unwrap())
}

/// The first Assistant of the valid catalog with one exact substring replaced.
fn varied(from: &str, to: &str) -> String {
    assert!(CATALOG.contains(from), "{from}");
    CATALOG.replacen(from, to, 1)
}

#[test]
fn a_valid_catalog_projects_to_the_python_stores_exact_bytes() {
    assert_eq!(projected(CATALOG, "pt").as_deref(), Some(PROJECTED));
}

#[test]
fn the_envelope_must_be_version_one_in_exactly_the_requested_locale() {
    for document in [
        varied("\"version\":1", "\"version\":true"),
        varied("\"version\":1", "\"version\":1.0"),
        varied("\"version\":1", "\"version\":2"),
        varied("\"locale\":\"pt\"", "\"locale\":\"en\""),
        varied("{\"version\":1,", "{\"extra\":1,\"version\":1,"),
        String::from("{\"version\":1,\"locale\":\"pt\",\"assistants\":{}}"),
        String::from("[]"),
    ] {
        assert_eq!(projected(&document, "pt"), None, "{document:.120}");
    }
    assert_eq!(
        projected(&varied("\"locale\":\"pt\"", "\"locale\":\"xx\""), "xx"),
        None
    );
}

#[test]
fn assistants_are_bounded_unique_and_sorted() {
    let one = &CATALOG
        [CATALOG.find("[{").unwrap() + 1..CATALOG.find(",{\"assistant_id\":\"hello-zz\"").unwrap()];
    let many = (0..=MAX_ASSISTANTS)
        .map(|index| one.replace("hello-world", &format!("a-{index:04}")))
        .collect::<Vec<_>>();
    let bounded = format!(
        "{{\"version\":1,\"locale\":\"pt\",\"assistants\":[{}]}}",
        many[..MAX_ASSISTANTS].join(",")
    );
    assert!(projected(&bounded, "pt").is_some());
    let over = format!(
        "{{\"version\":1,\"locale\":\"pt\",\"assistants\":[{}]}}",
        many.join(",")
    );
    assert_eq!(projected(&over, "pt"), None);
    assert_eq!(projected(&varied("hello-zz", "hello-world"), "pt"), None);
    assert_eq!(projected(&varied("hello-zz", "hello-aaa"), "pt"), None);
    assert_eq!(
        projected(
            &varied(
                "\"assistant_id\":\"hello-world\"",
                "\"assistant_id\":\"Hello\""
            ),
            "pt"
        ),
        None
    );
}

#[test]
fn every_assistant_scalar_field_has_its_exact_shape() {
    let refusals = [
        (
            "\"assistant_id\":\"hello-world\",",
            "\"assistant_id\":\"hello-world\",\"extra\":1,",
        ),
        (
            "\"assistant_version\":\"10.0.0\"",
            "\"assistant_version\":\"01.0.0\"",
        ),
        (
            "\"assistant_version\":\"10.0.0\"",
            "\"assistant_version\":10",
        ),
        (
            "\"source_digest\":\"sha256:a",
            "\"source_digest\":\"sha256:A",
        ),
        ("\"icon_digest\":\"sha256:b", "\"icon_digest\":\"sha256:B"),
        (
            "\"github\":\"https://github.com/TheShimpz/hello-world\"",
            "\"github\":\"https://example.com/x\"",
        ),
        ("[\"linux/amd64\",\"linux/arm64\"]", "[\"linux/amd64\"]"),
        ("\"name\":\"Hello World\"", "\"name\":\" Hello World\""),
        ("\"name\":\"Hello World\"", "\"name\":\"\""),
        ("\"name\":\"Hello World\"", "\"name\":\"Hello\\u007fWorld\""),
        ("\"name\":\"Hello World\"", "\"name\":\"Hello\\nWorld\""),
        ("\"name\":\"Hello World\"", "\"name\":7"),
        (
            "\"summary\":\"Greets the Team.\"",
            "\"summary\":\"Greets the Team.\\u00a0\"",
        ),
        (
            "\"description\":\"Greets the Team and keeps",
            "\"description\":\"Bidi\\u202e and keeps",
        ),
        (
            "\"description\":\"Greets the Team and keeps",
            "\"description\":\"e\\u0301 and keeps",
        ),
        (
            "\"links\":{\"site\"",
            "\"links\":{\"mastodon\":\"https://mastodon.social/@a\",\"site\"",
        ),
    ];
    for (from, to) in refusals {
        assert_eq!(projected(&varied(from, to), "pt"), None, "{to}");
    }
}

#[test]
fn a_name_holds_at_most_eighty_characters() {
    let long = format!("\"name\":\"{}\"", "n".repeat(81));
    assert_eq!(
        projected(&varied("\"name\":\"Hello World\"", &long), "pt"),
        None
    );
    let longest = format!("\"name\":\"{}\"", "n".repeat(80));
    assert!(projected(&varied("\"name\":\"Hello World\"", &longest), "pt").is_some());
}

#[test]
fn creators_and_allowed_hosts_are_closed_lists() {
    let refusals = [
        ("\"creators\":[\"@shimpz\"]", "\"creators\":[]"),
        ("\"creators\":[\"@shimpz\"]", "\"creators\":[\"shimpz\"]"),
        (
            "\"creators\":[\"@shimpz\"]",
            "\"creators\":[\"@shimpz\",\"@shimpz\"]",
        ),
        ("\"creators\":[\"@shimpz\"]", "\"creators\":[\"\"]"),
        ("\"creators\":[\"@shimpz\"]", "\"creators\":\"@shimpz\""),
        ("\"creators\":[\"@shimpz\"]", "\"creators\":[7]"),
        (
            "\"allowed_hosts\":[\"api.example.com\"]",
            "\"allowed_hosts\":[\"API.example.com\"]",
        ),
        (
            "\"allowed_hosts\":[\"api.example.com\"]",
            "\"allowed_hosts\":7",
        ),
    ];
    for (from, to) in refusals {
        assert_eq!(projected(&varied(from, to), "pt"), None, "{to}");
    }
    let crowded = format!(
        "\"creators\":[{}]",
        (0..17)
            .map(|index| format!("\"@c-{index:02}\""))
            .collect::<Vec<_>>()
            .join(",")
    );
    assert_eq!(
        projected(&varied("\"creators\":[\"@shimpz\"]", &crowded), "pt"),
        None
    );
}

#[test]
fn integrations_are_closed_sorted_and_name_their_provider() {
    let refusals = [
        ("\"scopes\":[\"repo:read\"]", "\"scopes\":[]"),
        ("\"scopes\":[\"repo:read\"]", "\"scopes\":[\"Repo:read\"]"),
        ("\"scopes\":[\"repo:read\"]", "\"scopes\":7"),
        (
            "{\"id\":\"github\",\"provider\":\"github\"",
            "{\"id\":\"github\",\"provider\":\"gitlab\"",
        ),
        (
            "{\"id\":\"github\",\"provider\":\"github\"",
            "{\"id\":\"GitHub\",\"provider\":\"GitHub\"",
        ),
        (
            "{\"id\":\"github\",\"provider\":\"github\",",
            "{\"id\":\"github\",\"x\":1,\"provider\":\"github\",",
        ),
        (
            "\"integrations\":[{\"id\":\"github\"",
            "\"integrations\":[{\"id\":\"zeta\",\"provider\":\"zeta\",\"scopes\":[\"a\"]},{\"id\":\"github\"",
        ),
        (
            "\"integrations\":[{\"id\":\"github\",\"provider\":\"github\",\"scopes\":[\"repo:read\"]}]",
            "\"integrations\":{}",
        ),
    ];
    for (from, to) in refusals {
        assert_eq!(projected(&varied(from, to), "pt"), None, "{to}");
    }
    let many = (0..17)
        .map(|index| {
            format!("{{\"id\":\"p-{index:02}\",\"provider\":\"p-{index:02}\",\"scopes\":[\"a\"]}}")
        })
        .collect::<Vec<_>>();
    let crowded = format!("\"integrations\":[{}]", many.join(","));
    let from =
        "\"integrations\":[{\"id\":\"github\",\"provider\":\"github\",\"scopes\":[\"repo:read\"]}]";
    assert_eq!(projected(&varied(from, &crowded), "pt"), None);
}

#[test]
fn stored_inputs_are_closed_password_inputs_with_localized_copy() {
    let refusals = [
        ("\"kind\":\"password\"", "\"kind\":\"text\""),
        ("{\"id\":\"api-token\",\"kind\"", "{\"id\":\"Api\",\"kind\""),
        (
            "\"help_url\":\"https://dashboard.example.com/api-keys\"",
            "\"help_url\":\"http://example.com\"",
        ),
        ("\"label\":\"API token\"", "\"label\":\"API\\ntoken\""),
        (
            "\"description\":\"Create an API token",
            "\"description\":\"e\\u0301 an API token",
        ),
        (
            "{\"id\":\"api-token\",\"kind\"",
            "{\"x\":1,\"id\":\"api-token\",\"kind\"",
        ),
        (
            "\"stored_inputs\":[{\"id\":\"api-token\"",
            "\"stored_inputs\":7,\"x\":[{\"id\":\"api-token\"",
        ),
    ];
    for (from, to) in refusals {
        assert_eq!(projected(&varied(from, to), "pt"), None, "{to}");
    }
    let input = "{\"id\":\"api-token\",\"kind\":\"password\",\"label\":\"API token\",\"description\":\"Create an API token in the example dashboard and copy it.\",\"help_url\":\"https://dashboard.example.com/api-keys\"}";
    let twice = format!("\"stored_inputs\":[{input},{input}]");
    assert_eq!(
        projected(
            &varied(&format!("\"stored_inputs\":[{input}]"), &twice),
            "pt"
        ),
        None
    );
    let nine = format!(
        "\"stored_inputs\":[{}]",
        (0..9)
            .map(|index| input.replace("api-token", &format!("k-{index}")))
            .collect::<Vec<_>>()
            .join(",")
    );
    assert_eq!(
        projected(
            &varied(&format!("\"stored_inputs\":[{input}]"), &nine),
            "pt"
        ),
        None
    );
}

#[test]
fn actions_are_bounded_unique_and_reference_only_declared_inputs() {
    let refusals = [
        ("\"effect\":\"read_only\"", "\"effect\":\"destructive\""),
        ("{\"id\":\"hello\",", "{\"id\":\"Hello\","),
        ("{\"id\":\"hello\",", "{\"id\":\"hello\",\"command\":\"x\","),
        (
            "\"human_requests\":[\"approval\",\"input:text\"]",
            "\"human_requests\":[\"unknown\"]",
        ),
        (
            "\"human_requests\":[\"approval\",\"input:text\"]",
            "\"human_requests\":[\"approval\",\"auth:totp\"]",
        ),
        (
            "\"human_requests\":[\"approval\",\"input:text\"]",
            "\"human_requests\":7",
        ),
        (
            "\"integrations\":[\"github\"],\"stored_inputs\":[\"api-token\"]",
            "\"integrations\":[\"GitHub\"],\"stored_inputs\":[\"api-token\"]",
        ),
        (
            "\"integrations\":[\"github\"],\"stored_inputs\":[\"api-token\"]",
            "\"integrations\":7,\"stored_inputs\":[\"api-token\"]",
        ),
        (
            "\"stored_inputs\":[\"api-token\"],\"human",
            "\"stored_inputs\":[\"undeclared\"],\"human",
        ),
        (
            "\"stored_inputs\":[\"api-token\"],\"human",
            "\"stored_inputs\":7,\"human",
        ),
        (
            "\"description\":\"Say hello.\"",
            "\"description\":\"Say hello. \"",
        ),
        ("\"actions\":[{", "\"actions\":[],\"x\":[{"),
        ("\"actions\":[{", "\"actions\":7,\"x\":[{"),
    ];
    for (from, to) in refusals {
        assert_eq!(projected(&varied(from, to), "pt"), None, "{to}");
    }
}

#[test]
fn actions_are_unique_and_at_most_one_hundred_twenty_eight() {
    let start = CATALOG.find("\"actions\":[").unwrap() + "\"actions\":[".len();
    let end = start + CATALOG[start..].find("}]").unwrap() + 1;
    let action = &CATALOG[start..end];
    let twice = format!("{action},{action}");
    assert_eq!(projected(&CATALOG.replacen(action, &twice, 1), "pt"), None);
    let many = (0..129)
        .map(|index| action.replace("\"hello\"", &format!("\"a-{index:03}\"")))
        .collect::<Vec<_>>();
    assert!(projected(&CATALOG.replacen(action, &many[..128].join(","), 1), "pt").is_some());
    assert_eq!(
        projected(&CATALOG.replacen(action, &many.join(","), 1), "pt"),
        None
    );
}
