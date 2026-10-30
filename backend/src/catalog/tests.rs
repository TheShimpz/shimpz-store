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
fn the_locale_is_exactly_one_closed_locale_query() {
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
    ] {
        assert_eq!(locale(query), None, "{query:?}");
    }
}

#[tokio::test]
async fn a_served_catalog_says_how_old_it_is_and_refusals_are_uncached() {
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
async fn an_icon_needs_two_well_formed_digests_before_developers_is_asked() {
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
