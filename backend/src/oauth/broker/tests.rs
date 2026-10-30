use std::{sync::Arc, time::Duration};

use super::{
    Broker, CAPACITY, CallbackMode, Completion, PendingAuthorization, challenge_of, nonce,
    random_binding, random_claim, unused,
};
use crate::oauth::{
    BrokerError,
    shape::Scopes,
    testing::{Fake, broker, latest_authorization, neuron_answer, reply},
};

const VERIFIER: &str = "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv";
const CODE: &str = "code-0000000000000";
const SCOPES: [&str; 2] = ["dns.read", "zone.read"];

fn local_state(seed: char) -> String {
    seed.to_string().repeat(43)
}

/// Start for `state` and complete the callback; the claim and the completion.
async fn authorized(fake: &Fake, broker: &Broker, state: &str, mode: CallbackMode) -> Completion {
    broker
        .start(state, &challenge_of(VERIFIER), mode, &SCOPES)
        .await
        .unwrap();
    let (broker_state, _) = latest_authorization(fake);
    broker
        .callback(&broker_state, CODE, &["zone.read", "dns.read"])
        .await
        .unwrap()
}

fn claim_of(completion: &Completion) -> String {
    match completion {
        Completion::Redirect(location) => location.rsplit("claim=").next().unwrap().to_owned(),
        Completion::OutOfBand(code) => code.rsplit('.').next().unwrap().to_owned(),
    }
}

fn counts(broker: &Broker) -> (usize, usize, usize, usize) {
    let state = broker.state();
    (
        state.authorizations.len(),
        state.grants.len(),
        state.active.len(),
        state.reservations,
    )
}

#[tokio::test]
async fn a_start_callback_claim_refresh_and_revoke_complete_the_flow() {
    let (fake, broker, _clock) = broker(neuron_answer).await;
    let state = local_state('L');
    let completion = authorized(&fake, &broker, &state, CallbackMode::Loopback).await;
    let claim = claim_of(&completion);
    assert_eq!(
        completion,
        Completion::Redirect(format!(
            "http://127.0.0.1:7777/api/oauth/cloudflare/callback?state={state}&claim={claim}"
        ))
    );
    let (_, challenge) = latest_authorization(&fake);
    let exchanged = fake.received.lock().unwrap().last().unwrap().body.clone();
    assert!(exchanged.contains("\"code\":\"code-0000000000000\""));
    let verifier = strict_json::parse(exchanged.as_bytes()).unwrap();
    let Some(strict_json::Value::String(broker_verifier)) = verifier.get("code_verifier") else {
        panic!("a verifier");
    };
    assert_eq!(challenge_of(broker_verifier), challenge);
    assert_eq!(counts(&broker), (0, 1, 1, 0));
    let handoff = broker.claim(&claim, &state, VERIFIER).unwrap();
    assert_eq!(handoff.tokens.expires_in, 3600);
    assert_eq!(handoff.scopes.joined(), "dns.read zone.read");
    assert_eq!(counts(&broker), (0, 0, 0, 0));
    let scopes = Scopes::sorted(&SCOPES).unwrap();
    let refreshed = broker
        .refresh("refresh-token-001", &handoff.lease, &scopes)
        .await
        .unwrap();
    assert!(refreshed.lease.starts_with("l3."));
    assert_eq!(
        broker.revoke("access-token-0001", &refreshed.lease).await,
        Ok(())
    );
}

#[tokio::test]
async fn the_local_domain_and_out_of_band_modes_hand_over_the_claim_their_way() {
    let (fake, broker, _clock) = broker(neuron_answer).await;
    let domain = authorized(&fake, &broker, &local_state('D'), CallbackMode::LocalDomain).await;
    let Completion::Redirect(location) = domain else {
        panic!("a redirect");
    };
    assert!(
        location.starts_with("https://local.shimpz.com/api/oauth/cloudflare/callback?state=DDD")
    );
    let state = local_state('O');
    let out_of_band = authorized(&fake, &broker, &state, CallbackMode::OutOfBand).await;
    let claim = claim_of(&out_of_band);
    assert_eq!(
        out_of_band,
        Completion::OutOfBand(format!("c1.{state}.{claim}"))
    );
    assert_eq!(claim.len(), 64);
}

#[tokio::test]
async fn a_start_refuses_malformed_values_an_active_local_state_and_a_full_capacity() {
    let (_fake, broker, _clock) = broker(neuron_answer).await;
    let challenge = challenge_of(VERIFIER);
    let state = local_state('S');
    let mode = CallbackMode::Loopback;
    assert_eq!(
        broker.start("short", &challenge, mode, &SCOPES).await,
        Err(BrokerError)
    );
    assert_eq!(
        broker.start(&state, "short", mode, &SCOPES).await,
        Err(BrokerError)
    );
    assert_eq!(
        broker
            .start(&state, &challenge, mode, &["zone.read", "dns.read"])
            .await,
        Err(BrokerError)
    );
    assert!(
        broker
            .start(&state, &challenge, mode, &SCOPES)
            .await
            .is_ok()
    );
    assert_eq!(
        broker.start(&state, &challenge, mode, &SCOPES).await,
        Err(BrokerError)
    );
    fill_authorizations(&broker, CAPACITY - 1);
    assert_eq!(
        broker
            .start(&local_state('T'), &challenge, mode, &SCOPES)
            .await,
        Err(BrokerError)
    );
    assert_eq!(counts(&broker).0, CAPACITY);
}

fn pending(local_state: &str, expires_at: Duration) -> PendingAuthorization {
    PendingAuthorization {
        local_state: local_state.to_owned(),
        challenge: challenge_of(VERIFIER),
        mode: CallbackMode::Loopback,
        verifier: VERIFIER.to_owned(),
        scopes: Scopes::sorted(&SCOPES).unwrap(),
        expires_at,
    }
}

fn fill_authorizations(broker: &Broker, count: usize) {
    let mut state = broker.state();
    for index in 0..count {
        state.authorizations.insert(
            format!("filler-{index}"),
            pending(&format!("f-{index}"), Duration::MAX),
        );
    }
}

#[tokio::test]
async fn a_failed_authorization_releases_its_local_state() {
    let (_fake, broker, _clock) =
        broker(|_| reply("502 Bad Gateway", "application/json", "{}")).await;
    let state = local_state('F');
    let challenge = challenge_of(VERIFIER);
    for _ in 0..2 {
        assert_eq!(
            broker
                .start(&state, &challenge, CallbackMode::Loopback, &SCOPES)
                .await,
            Err(BrokerError)
        );
    }
    assert_eq!(counts(&broker), (0, 0, 0, 0));
}

#[tokio::test]
async fn a_callback_refuses_malformed_values_and_unknown_authorizations() {
    let (_fake, broker, _clock) = broker(neuron_answer).await;
    let known = random_binding();
    for (state, code, scopes) in [
        ("short", CODE, &SCOPES[..]),
        (known.as_str(), "short", &SCOPES[..]),
        (known.as_str(), "code with space!", &SCOPES[..]),
        (known.as_str(), CODE, &["dns.read", "dns.read"][..]),
        (known.as_str(), CODE, &SCOPES[..]),
    ] {
        assert_eq!(
            broker.callback(state, code, scopes).await,
            Err(BrokerError),
            "{state} {code}"
        );
    }
}

#[tokio::test]
async fn a_callback_with_other_scopes_or_a_failed_exchange_releases_the_local_state() {
    let (fake, broker, _clock) = broker(|recorded| {
        if recorded.head.contains("/exchange ") {
            reply("502 Bad Gateway", "application/json", "{}")
        } else {
            neuron_answer(recorded)
        }
    })
    .await;
    let state = local_state('M');
    let challenge = challenge_of(VERIFIER);
    broker
        .start(&state, &challenge, CallbackMode::Loopback, &SCOPES)
        .await
        .unwrap();
    let (broker_state, _) = latest_authorization(&fake);
    assert_eq!(
        broker.callback(&broker_state, CODE, &["dns.read"]).await,
        Err(BrokerError)
    );
    assert_eq!(counts(&broker), (0, 0, 0, 0));
    broker
        .start(&state, &challenge, CallbackMode::Loopback, &SCOPES)
        .await
        .unwrap();
    let (broker_state, _) = latest_authorization(&fake);
    assert_eq!(
        broker.callback(&broker_state, CODE, &SCOPES).await,
        Err(BrokerError)
    );
    assert_eq!(counts(&broker), (0, 0, 0, 0));
}

#[tokio::test]
async fn a_callback_past_the_grant_capacity_keeps_the_authorization() {
    let (fake, broker, _clock) = broker(neuron_answer).await;
    broker
        .start(
            &local_state('C'),
            &challenge_of(VERIFIER),
            CallbackMode::Loopback,
            &SCOPES,
        )
        .await
        .unwrap();
    let (broker_state, _) = latest_authorization(&fake);
    broker.state().reservations = CAPACITY;
    assert_eq!(
        broker.callback(&broker_state, CODE, &SCOPES).await,
        Err(BrokerError)
    );
    broker.state().reservations = 0;
    assert!(broker.callback(&broker_state, CODE, &SCOPES).await.is_ok());
}

#[tokio::test]
async fn a_claim_needs_its_shape_state_and_verifier_and_an_unproven_claim_stays() {
    let (fake, broker, _clock) = broker(neuron_answer).await;
    let state = local_state('P');
    let claim = claim_of(&authorized(&fake, &broker, &state, CallbackMode::Loopback).await);
    let other_verifier = "w".repeat(43);
    for (claim, state, verifier) in [
        (claim.to_uppercase(), state.clone(), VERIFIER.to_owned()),
        (claim[..63].to_owned(), state.clone(), VERIFIER.to_owned()),
        (claim.clone(), "short".to_owned(), VERIFIER.to_owned()),
        (claim.clone(), state.clone(), "v".repeat(42)),
        (claim.clone(), local_state('Q'), VERIFIER.to_owned()),
        (claim.clone(), state.clone(), other_verifier),
        ("0".repeat(64), state.clone(), VERIFIER.to_owned()),
    ] {
        assert!(
            broker.claim(&claim, &state, &verifier).is_err(),
            "{claim} {state} {verifier}"
        );
    }
    assert!(broker.claim(&claim, &state, VERIFIER).is_ok());
    assert!(broker.claim(&claim, &state, VERIFIER).is_err());
}

#[tokio::test]
async fn a_claim_with_too_little_token_lifetime_left_is_consumed_and_refused() {
    let (fake, broker, clock) = broker(neuron_answer).await;
    let state = local_state('R');
    let claim = claim_of(&authorized(&fake, &broker, &state, CallbackMode::Loopback).await);
    let mut grants = broker.state();
    let grant = grants.grants.get_mut(&claim).unwrap();
    grant.token_expires_at =
        crate::clock::Clock::monotonic(&*clock) + Duration::from_millis(29_999);
    drop(grants);
    assert!(broker.claim(&claim, &state, VERIFIER).is_err());
    assert_eq!(counts(&broker), (0, 0, 0, 0));
}

#[tokio::test]
async fn a_claim_whose_lease_cannot_be_signed_is_consumed_and_refused() {
    let (fake, broker, _clock) = broker(neuron_answer).await;
    let state = local_state('K');
    let claim = claim_of(&authorized(&fake, &broker, &state, CallbackMode::Loopback).await);
    std::fs::remove_file(fake.directory.path().join("lease-key")).unwrap();
    assert!(broker.claim(&claim, &state, VERIFIER).is_err());
    assert_eq!(counts(&broker), (0, 0, 0, 0));
}

#[tokio::test]
async fn authorizations_and_grants_expire_after_five_minutes_and_release_their_local_states() {
    let (fake, broker, clock) = broker(neuron_answer).await;
    let challenge = challenge_of(VERIFIER);
    broker
        .start(
            &local_state('A'),
            &challenge,
            CallbackMode::Loopback,
            &SCOPES,
        )
        .await
        .unwrap();
    let (expiring, _) = latest_authorization(&fake);
    let claim =
        claim_of(&authorized(&fake, &broker, &local_state('G'), CallbackMode::Loopback).await);
    clock.step(Duration::from_secs(299));
    assert_eq!(counts(&broker), (1, 1, 2, 0));
    clock.step(Duration::from_secs(1));
    assert_eq!(
        broker.callback(&expiring, CODE, &SCOPES).await,
        Err(BrokerError)
    );
    assert_eq!(counts(&broker), (0, 0, 0, 0));
    assert!(broker.claim(&claim, &local_state('G'), VERIFIER).is_err());
}

#[tokio::test]
async fn refresh_and_revoke_need_a_token_and_a_lease_naming_it() {
    let (_fake, broker, _clock) = broker(neuron_answer).await;
    let scopes = Scopes::sorted(&SCOPES).unwrap();
    assert!(broker.refresh("short", "l3.x", &scopes).await.is_err());
    assert!(
        broker
            .refresh("refresh-token-001", "l3.x", &scopes)
            .await
            .is_err()
    );
    assert_eq!(broker.revoke("short", "l3.x").await, Err(BrokerError));
    assert_eq!(
        broker.revoke("access-token-0001", "l3.x").await,
        Err(BrokerError)
    );
}

#[tokio::test]
async fn a_start_whose_authorization_a_callback_consumed_leaves_the_callbacks_state_alone() {
    let (fake, broker, _clock) = broker(|recorded| {
        if recorded.head.contains("/authorization ") {
            reply("502 Bad Gateway", "application/json", "{}")
        } else {
            neuron_answer(recorded)
        }
    })
    .await;
    let broker = Arc::new(broker);
    fake.held.send_replace(true);
    let starting = tokio::spawn({
        let broker = Arc::clone(&broker);
        async move {
            broker
                .start(
                    &local_state('X'),
                    &challenge_of(VERIFIER),
                    CallbackMode::Loopback,
                    &SCOPES,
                )
                .await
        }
    });
    while fake.received.lock().unwrap().is_empty() {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    let (broker_state, _) = latest_authorization(&fake);
    let (reservation, _pending) = broker.reserve(&broker_state, Duration::ZERO).unwrap();
    fake.held.send_replace(false);
    assert_eq!(starting.await.unwrap(), Err(BrokerError));
    assert_eq!(counts(&broker), (0, 0, 1, 1));
    drop(reservation);
    assert_eq!(counts(&broker), (0, 0, 0, 0));
}

#[tokio::test]
async fn a_panicking_operation_restores_reservations_and_local_state() {
    let (fake, broker, _clock) = broker(neuron_answer).await;
    let broker = Arc::new(broker);
    broker
        .start(
            &local_state('Z'),
            &challenge_of(VERIFIER),
            CallbackMode::Loopback,
            &SCOPES,
        )
        .await
        .unwrap();
    let (broker_state, _) = latest_authorization(&fake);
    let panicking = tokio::spawn({
        let broker = Arc::clone(&broker);
        async move {
            let _reservation = broker.reserve(&broker_state, Duration::ZERO).unwrap();
            assert_eq!(counts(&broker), (0, 0, 1, 1));
            panic!("an operation failed unexpectedly");
        }
    });
    assert!(panicking.await.unwrap_err().is_panic());
    assert_eq!(counts(&broker), (0, 0, 0, 0));
}

#[test]
fn a_colliding_key_is_drawn_again() {
    let mut draws = vec!["fresh".to_owned(), "taken".to_owned()];
    let key = unused(&|key| key == "taken", &mut || draws.pop().unwrap());
    assert_eq!(key, "fresh");
}

#[test]
fn random_values_have_their_python_shapes() {
    let binding = random_binding();
    assert_eq!(binding.len(), 43);
    assert_ne!(binding, random_binding());
    let claim = random_claim();
    assert_eq!(claim.len(), 64);
    assert!(
        claim
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
    );
    assert_eq!(nonce().len(), 24);
    assert_eq!(challenge_of(VERIFIER).len(), 43);
}

#[test]
fn only_the_three_callback_modes_parse() {
    assert_eq!(
        CallbackMode::parse("loopback"),
        Some(CallbackMode::Loopback)
    );
    assert_eq!(
        CallbackMode::parse("local-domain"),
        Some(CallbackMode::LocalDomain)
    );
    assert_eq!(
        CallbackMode::parse("out-of-band"),
        Some(CallbackMode::OutOfBand)
    );
    assert_eq!(CallbackMode::parse("remote"), None);
}
