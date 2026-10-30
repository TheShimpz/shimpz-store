use std::{sync::Arc, time::Duration};

use http::{StatusCode, header};
use sha2::{Digest, Sha256};

use super::{Catalog, locale};
use crate::{
    catalog::testing::{Script, fake, ok},
    clock::ManualClock,
    response::Reply,
};

const CATALOG: &str = include_str!("project/catalog.json");

fn header<'a>(reply: &'a Reply, name: &header::HeaderName) -> &'a str {
    reply.header(name).unwrap().to_str().unwrap()
}

#[test]
fn public_route_refuses_any_query_but_one_closed_locale() {
    for (query, expected) in [
        (Some("locale=en"), Some("en")),
        (Some("locale=zh"), Some("zh")),
    ] {
        assert_eq!(locale(query), expected);
    }
    for query in [
        None,
        Some(""),
        Some("locale=EN"),
        Some("locale=en&x=1"),
        Some("x=1&locale=en"),
        Some("locale=e%6e"),
        Some("locale="),
        Some("locale=it"),
        Some("locale=pt&locale=en"),
        Some("locale=pt&page=2"),
        Some("page=2&locale=pt"),
    ] {
        assert_eq!(locale(query), None, "{query:?}");
    }
}

#[tokio::test]
async fn a_kept_catalog_tells_later_caches_how_old_it_is() {
    let body = Sha256::digest(b"png");
    let _ = body;
    let fake = fake(|target| {
        if target.ends_with("icon.png") {
            Script::Reply(ok("image/png", b"png"))
        } else {
            Script::Reply(ok("application/json", CATALOG.as_bytes()))
        }
    })
    .await;
    let clock = Arc::new(ManualClock::at(0));
    let catalog = Catalog::new(&fake.developers, clock.clone(), Duration::from_secs(5));
    let served = catalog.catalog(Some("locale=pt")).await;
    assert_eq!(served.status, StatusCode::OK);
    assert_eq!(
        header(&served, &header::CACHE_CONTROL),
        "public, max-age=60, s-maxage=300"
    );
    clock.step(Duration::from_millis(7_900));
    assert_eq!(
        header(&catalog.catalog(Some("locale=pt")).await, &header::AGE),
        "7"
    );
    let invalid = catalog.catalog(Some("locale=xx")).await;
    assert_eq!(
        (invalid.status, header(&invalid, &header::CACHE_CONTROL)),
        (StatusCode::BAD_REQUEST, "no-store")
    );
    assert_eq!(
        invalid.body,
        &b"{\"detail\":\"Assistant catalog locale is invalid\"}"[..]
    );
    let unavailable = catalog.catalog(Some("locale=en")).await;
    assert_eq!(unavailable.status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(
        unavailable.body,
        &b"{\"detail\":\"Assistant catalog is unavailable\"}"[..]
    );
}

#[tokio::test]
async fn public_icon_route_refuses_a_malformed_digest_before_developers() {
    let fake = fake(|_| Script::Reply(ok("image/png", b"png"))).await;
    let catalog = Catalog::new(
        &fake.developers,
        Arc::new(ManualClock::at(0)),
        Duration::from_secs(5),
    );
    let digest = super::icons::hex(&Sha256::digest(b"png"));
    let good = "a".repeat(64);
    let served = catalog.icon(&good, &digest).await;
    assert_eq!(
        (served.status, served.body.as_ref()),
        (StatusCode::OK, &b"png"[..])
    );
    assert_eq!(
        header(&served, &header::CACHE_CONTROL),
        "public, max-age=31536000, immutable"
    );
    assert_eq!(header(&served, &header::CONTENT_TYPE), "image/png");
    for (source, icon) in [
        (good.to_uppercase(), digest.clone()),
        (good.clone(), digest[..63].to_owned()),
    ] {
        let refused = catalog.icon(&source, &icon).await;
        assert_eq!(refused.status, StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(header(&refused, &header::CACHE_CONTROL), "no-store");
    }
    assert_eq!(
        catalog.icon(&good, &"0".repeat(64)).await.status,
        StatusCode::SERVICE_UNAVAILABLE
    );
    assert_eq!(fake.calls.lock().unwrap().values().sum::<usize>(), 2);
}

/// The fixture catalog in the locale a Developers target asks for.
fn in_locale(target: &str) -> Script {
    let locale = target.rsplit('=').next().unwrap().to_owned();
    let document = CATALOG.replacen("\"locale\":\"pt\"", &format!("\"locale\":\"{locale}\""), 1);
    Script::Reply(ok("application/json", document.as_bytes()))
}

fn catalog_over(fake: &crate::catalog::testing::Fake) -> Catalog {
    Catalog::new(
        &fake.developers,
        Arc::new(ManualClock::at(0)),
        Duration::from_secs(5),
    )
}

#[tokio::test]
async fn public_route_caches_only_a_valid_developers_catalog_per_locale() {
    let fake = fake(in_locale).await;
    let catalog = catalog_over(&fake);
    for locale in ["en", "pt"] {
        let served = catalog.catalog(Some(&format!("locale={locale}"))).await;
        assert_eq!(served.status, StatusCode::OK);
        assert_eq!(
            header(&served, &header::CACHE_CONTROL),
            "public, max-age=60, s-maxage=300"
        );
        let body = String::from_utf8(served.body.to_vec()).unwrap();
        assert!(body.contains(&format!("\"locale\":\"{locale}\"")), "{body}");
        assert_eq!(
            fake.calls(&format!("/api/v1/assistants?locale={locale}")),
            1
        );
    }
}

#[tokio::test]
async fn public_route_refuses_a_catalog_in_another_locale() {
    let fake = fake(|_| Script::Reply(ok("application/json", CATALOG.as_bytes()))).await;
    let refused = catalog_over(&fake).catalog(Some("locale=en")).await;
    assert_eq!(
        (refused.status, header(&refused, &header::CACHE_CONTROL)),
        (StatusCode::SERVICE_UNAVAILABLE, "no-store")
    );
}

#[tokio::test]
async fn public_route_fails_closed_without_cache() {
    for reply in [
        b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 2\r\n\r\n{}".to_vec(),
        ok(
            "application/json",
            b"{\"version\":1,\"locale\":\"en\",\"assistants\":\"bad\"}",
        ),
    ] {
        let fake = fake(move |_| Script::Reply(reply.clone())).await;
        let refused = catalog_over(&fake).catalog(Some("locale=en")).await;
        assert_eq!(refused.status, StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(header(&refused, &header::CACHE_CONTROL), "no-store");
        assert_eq!(
            refused.body,
            &b"{\"detail\":\"Assistant catalog is unavailable\"}"[..]
        );
    }
}

#[tokio::test]
async fn public_icon_route_verifies_and_immutably_caches_exact_bytes() {
    let fake = fake(|_| Script::Reply(ok("image/png", b"canonical icon"))).await;
    let catalog = catalog_over(&fake);
    let digest = super::icons::hex(&Sha256::digest(b"canonical icon"));
    for _ in 0..2 {
        let served = catalog.icon(&"a".repeat(64), &digest).await;
        assert_eq!(
            (served.status, &served.body[..]),
            (StatusCode::OK, &b"canonical icon"[..])
        );
        assert_eq!(header(&served, &header::CONTENT_TYPE), "image/png");
        assert_eq!(
            header(&served, &header::CACHE_CONTROL),
            "public, max-age=31536000, immutable"
        );
    }
    let target = format!(
        "/api/v1/assistant-publications/sha256:{}/icon.png",
        "a".repeat(64)
    );
    assert_eq!(fake.calls(&target), 1);
}

#[tokio::test]
async fn public_icon_route_fails_closed_on_digest_mismatch() {
    let fake = fake(|_| Script::Reply(ok("image/png", b"wrong icon"))).await;
    let refused = catalog_over(&fake)
        .icon(&"a".repeat(64), &"b".repeat(64))
        .await;
    assert_eq!(
        (refused.status, header(&refused, &header::CACHE_CONTROL)),
        (StatusCode::SERVICE_UNAVAILABLE, "no-store")
    );
}

#[tokio::test]
async fn a_grid_of_cold_icons_waits_on_the_loop_and_leaves_the_catalog_its_executor() {
    let fake = fake(|target| {
        if target.ends_with("icon.png") {
            Script::Reply(ok("image/png", target.as_bytes()))
        } else {
            in_locale(target)
        }
    })
    .await;
    let catalog = Arc::new(catalog_over(&fake));
    let icons: Vec<_> = (0..24)
        .map(|index| {
            let catalog = Arc::clone(&catalog);
            let source = format!("{index:064x}");
            let target = format!("/api/v1/assistant-publications/sha256:{source}/icon.png");
            let digest = super::icons::hex(&Sha256::digest(target.as_bytes()));
            tokio::spawn(async move { catalog.icon(&source, &digest).await.status })
        })
        .collect();
    assert_eq!(
        catalog.catalog(Some("locale=en")).await.status,
        StatusCode::OK
    );
    for icon in icons {
        assert_eq!(icon.await.unwrap(), StatusCode::OK);
    }
}

#[test]
fn a_full_utf8_catalog_is_served_as_utf8_within_the_consumer_byte_limit() {
    let first = CATALOG.find("{\"assistant_id\"").unwrap();
    let second = CATALOG[first + 1..].find("{\"assistant_id\"").unwrap() + first + 1;
    let template = CATALOG[first..second - 1]
        .replace(
            "\"name\":\"Hello World\"",
            &format!("\"name\":\"{}\"", "\u{c1}".repeat(80)),
        )
        .replace(
            "\"summary\":\"Greets the Team.\"",
            &format!("\"summary\":\"{}\"", "\u{c9}".repeat(80)),
        )
        .replace(
            "\"description\":\"Greets the Team and keeps the greeting short.\"",
            &format!("\"description\":\"{}\"", "\u{d3}".repeat(500)),
        )
        .replace(
            "\"allowed_hosts\":[\"api.example.com\"]",
            &format!(
                "\"allowed_hosts\":[{}]",
                (0..16)
                    .map(|host| format!("\"{}{host:02}.example.com\"", "a".repeat(60)))
                    .collect::<Vec<_>>()
                    .join(",")
            ),
        );
    let assistants: Vec<String> = (0..1000)
        .map(|index| {
            template.replacen(
                "\"assistant_id\":\"hello-world\"",
                &format!("\"assistant_id\":\"assistant-{index:04}\""),
                1,
            )
        })
        .collect();
    let document = format!(
        "{{\"version\":1,\"locale\":\"en\",\"assistants\":[{}]}}",
        assistants.join(",")
    );
    let projected =
        super::project::project(&strict_json::parse(document.as_bytes()).unwrap(), "en").unwrap();
    assert!(projected.len() <= 4 * 1024 * 1024, "{}", projected.len());
    assert!(
        String::from_utf8(projected)
            .unwrap()
            .contains(&"\u{c1}".repeat(80))
    );
}
