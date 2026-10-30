//! The broker's state machine: one platform provider exchange bound to one local PKCE verifier and one-use claim.
//!
//! A start records a pending authorization under a fresh broker state and asks Neuron for the consent URL; the
//! callback consumes it, reserves grant capacity, exchanges the code with the broker's verifier, and stores the tokens
//! under a fresh claim; the claim hands them to the Local Space that proves its state and PKCE verifier, once. Refresh
//! and revoke need a lease ([`super::lease`]). Every intermediate state has a guard that restores the counters and
//! releases the local state unless the step commits, so a failure, a panic, or an abort leaves nothing behind.

use std::{
    collections::{HashMap, HashSet},
    sync::{Arc, Mutex, MutexGuard, PoisonError},
    time::Duration,
};

use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use sha2::{Digest, Sha256};
use subtle::ConstantTimeEq;

use super::{
    BrokerError,
    lease::LeaseSigner,
    neuron::{Neuron, Tokens},
    shape::{Scopes, binding, code, token},
};
use crate::clock::Clock;

/// The most pending authorizations, and the most grants and reservations together.
pub const CAPACITY: usize = 4096;
/// The automatic callback of a Local Admin on its own machine.
pub const LOCAL_CALLBACK: &str = "http://127.0.0.1:7777/api/oauth/cloudflare/callback";
/// The automatic callback of a Local Admin on its local domain.
pub const LOCAL_DOMAIN_CALLBACK: &str = "https://local.shimpz.com/api/oauth/cloudflare/callback";
const AUTHORIZATION_TTL: Duration = Duration::from_secs(300);
const GRANT_TTL: Duration = Duration::from_secs(300);
const MIN_TOKEN_SECONDS: u64 = 30;

/// Where the callback hands the claim to the Local Space.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CallbackMode {
    /// A redirect to the Local Admin on loopback.
    Loopback,
    /// A redirect to the Local Admin on its local domain.
    LocalDomain,
    /// A completion code the person copies into the Local Admin.
    OutOfBand,
}

impl CallbackMode {
    /// The mode a start names, or `None` for any other value.
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "loopback" => Some(Self::Loopback),
            "local-domain" => Some(Self::LocalDomain),
            "out-of-band" => Some(Self::OutOfBand),
            _ => None,
        }
    }

    const fn callback(self) -> Option<&'static str> {
        match self {
            Self::Loopback => Some(LOCAL_CALLBACK),
            Self::LocalDomain => Some(LOCAL_DOMAIN_CALLBACK),
            Self::OutOfBand => None,
        }
    }
}

/// How a completed callback hands over its claim.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Completion {
    /// Redirect the browser to this Local Admin URL.
    Redirect(String),
    /// Show this completion code.
    OutOfBand(String),
}

/// Tokens handed to a Local Space, with the lease that lets it refresh or revoke them.
pub struct Handoff {
    /// The tokens; `expires_in` is what remains of the access token's lifetime.
    pub tokens: Tokens,
    /// The scopes the tokens carry.
    pub scopes: Scopes,
    /// The lease over the tokens and scopes.
    pub lease: String,
}

struct PendingAuthorization {
    local_state: String,
    challenge: String,
    mode: CallbackMode,
    verifier: String,
    scopes: Scopes,
    expires_at: Duration,
}

struct PendingGrant {
    local_state: String,
    challenge: String,
    tokens: Tokens,
    token_expires_at: Duration,
    scopes: Scopes,
    expires_at: Duration,
}

#[derive(Default)]
struct State {
    authorizations: HashMap<String, PendingAuthorization>,
    grants: HashMap<String, PendingGrant>,
    active: HashSet<String>,
    reservations: usize,
}

impl State {
    /// Drop every authorization and grant whose lifetime ended by `now`, releasing their local states.
    fn expire(&mut self, now: Duration) {
        let active = &mut self.active;
        self.authorizations.retain(|_, pending| {
            let live = pending.expires_at > now;
            if !live {
                active.remove(&pending.local_state);
            }
            live
        });
        self.grants.retain(|_, grant| {
            let live = grant.expires_at > now;
            if !live {
                active.remove(&grant.local_state);
            }
            live
        });
    }
}

/// The broker: Neuron, the lease signer, the clock, and the pending state.
pub struct Broker {
    neuron: Neuron,
    signer: LeaseSigner,
    clock: Arc<dyn Clock>,
    state: Mutex<State>,
}

impl Broker {
    /// The deployed Store's broker on this clock.
    #[must_use]
    pub fn production(clock: Arc<dyn Clock>) -> Self {
        Self::new(
            Neuron::production(),
            LeaseSigner::production(Arc::clone(&clock)),
            clock,
        )
    }

    /// A broker over this Neuron client, lease signer, and clock.
    #[must_use]
    pub fn new(neuron: Neuron, signer: LeaseSigner, clock: Arc<dyn Clock>) -> Self {
        Self {
            neuron,
            signer,
            clock,
            state: Mutex::new(State::default()),
        }
    }

    /// Whether no authorization, grant, reservation, or local state is held.
    #[cfg(test)]
    pub(crate) fn idle(&self) -> bool {
        let state = self.state();
        let held = (
            state.authorizations.len(),
            state.grants.len(),
            state.active.len(),
            state.reservations,
        );
        held == (0, 0, 0, 0)
    }

    fn state(&self) -> MutexGuard<'_, State> {
        self.state.lock().unwrap_or_else(PoisonError::into_inner)
    }

    /// Record a pending authorization for this local state and challenge and return Cloudflare's consent URL.
    ///
    /// # Errors
    ///
    /// A value is malformed, the capacity is full, the local state is already active, or Neuron fails.
    pub async fn start(
        &self,
        local_state: &str,
        challenge: &str,
        mode: CallbackMode,
        scopes: &[&str],
    ) -> Result<String, BrokerError> {
        if !binding(local_state) || !binding(challenge) {
            return Err(BrokerError);
        }
        let scopes = Scopes::sorted(scopes)?;
        let now = self.clock.monotonic();
        let verifier = random_binding();
        let pkce = challenge_of(&verifier);
        let guard = {
            let mut state = self.state();
            state.expire(now);
            if state.authorizations.len() >= CAPACITY || state.active.contains(local_state) {
                return Err(BrokerError);
            }
            let broker_state = unused(
                &|key| state.authorizations.contains_key(key),
                &mut random_binding,
            );
            state.authorizations.insert(
                broker_state.clone(),
                PendingAuthorization {
                    local_state: local_state.to_owned(),
                    challenge: challenge.to_owned(),
                    mode,
                    verifier,
                    scopes: scopes.clone(),
                    expires_at: now + AUTHORIZATION_TTL,
                },
            );
            state.active.insert(local_state.to_owned());
            AuthorizationGuard {
                broker: self,
                broker_state,
                committed: false,
            }
        };
        let url = self
            .neuron
            .authorization(&guard.broker_state, &pkce, &scopes)
            .await?;
        guard.commit();
        Ok(url)
    }

    /// Complete the authorization Cloudflare returned to: exchange its code and store a one-use claim.
    ///
    /// # Errors
    ///
    /// A value is malformed, the capacity is full, the authorization is unknown or its scopes differ, or the exchange
    /// fails; a consumed authorization releases its local state.
    pub async fn callback(
        &self,
        broker_state: &str,
        authorization_code: &str,
        scopes: &[&str],
    ) -> Result<Completion, BrokerError> {
        if !binding(broker_state) || !code(authorization_code, 16, 4096) {
            return Err(BrokerError);
        }
        let returned = Scopes::returned(scopes)?;
        let now = self.clock.monotonic();
        let (reservation, pending) = self.reserve(broker_state, now)?;
        if returned != pending.scopes {
            return Err(BrokerError);
        }
        let tokens = self
            .neuron
            .exchange(authorization_code, &pending.verifier, &pending.scopes)
            .await?;
        let claim = reservation.convert(now, &pending, tokens);
        Ok(match pending.mode.callback() {
            None => Completion::OutOfBand(format!("c1.{}.{claim}", pending.local_state)),
            Some(callback) => Completion::Redirect(format!(
                "{callback}?state={}&claim={claim}",
                pending.local_state
            )),
        })
    }

    /// Consume the pending authorization under `broker_state` and reserve grant capacity for it.
    fn reserve(
        &self,
        broker_state: &str,
        now: Duration,
    ) -> Result<(ReservationGuard<'_>, PendingAuthorization), BrokerError> {
        let mut state = self.state();
        state.expire(now);
        if state.grants.len() + state.reservations >= CAPACITY {
            return Err(BrokerError);
        }
        let pending = state
            .authorizations
            .remove(broker_state)
            .ok_or(BrokerError)?;
        state.reservations += 1;
        let guard = ReservationGuard {
            broker: self,
            local_state: pending.local_state.clone(),
            armed: true,
        };
        Ok((guard, pending))
    }

    /// Hand the claimed tokens to the Local Space that proves the local state and the PKCE verifier, once.
    ///
    /// # Errors
    ///
    /// A value is malformed, the claim is unknown or unproven, too little token lifetime remains, or the lease cannot
    /// be signed; a proven claim is consumed either way.
    pub fn claim(
        &self,
        claim: &str,
        local_state: &str,
        verifier: &str,
    ) -> Result<Handoff, BrokerError> {
        let claim_shaped = claim.len() == 64
            && claim
                .bytes()
                .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'));
        if !claim_shaped || !binding(local_state) || !code(verifier, 43, 128) {
            return Err(BrokerError);
        }
        let now = self.clock.monotonic();
        let grant = {
            let mut state = self.state();
            state.expire(now);
            let proven = state.grants.get(claim).is_some_and(|grant| {
                let state_matches = grant.local_state.as_bytes().ct_eq(local_state.as_bytes());
                let challenge_matches = grant
                    .challenge
                    .as_bytes()
                    .ct_eq(challenge_of(verifier).as_bytes());
                bool::from(state_matches & challenge_matches)
            });
            let Some(grant) = proven.then(|| state.grants.remove(claim)).flatten() else {
                return Err(BrokerError);
            };
            state.active.remove(&grant.local_state);
            grant
        };
        let remaining = grant.token_expires_at.saturating_sub(now).as_secs();
        if remaining < MIN_TOKEN_SECONDS {
            return Err(BrokerError);
        }
        let mut tokens = grant.tokens;
        tokens.expires_in = i64::try_from(remaining).unwrap_or(i64::MAX);
        self.handoff(tokens, grant.scopes)
    }

    /// Refresh the tokens a valid lease names, for exactly the scopes it names.
    ///
    /// # Errors
    ///
    /// A value is malformed, the lease does not verify, or Neuron fails.
    pub async fn refresh(
        &self,
        refresh_token: &str,
        lease: &str,
        scopes: &Scopes,
    ) -> Result<Handoff, BrokerError> {
        if !token(refresh_token) {
            return Err(BrokerError);
        }
        self.signer
            .verify(lease, refresh_token, Some(&scopes.joined()))?;
        let tokens = self.neuron.refresh(refresh_token, scopes).await?;
        self.handoff(tokens, scopes.clone())
    }

    /// Revoke a token a valid lease names.
    ///
    /// # Errors
    ///
    /// The token is malformed, the lease does not verify, or Neuron fails.
    pub async fn revoke(&self, revoked: &str, lease: &str) -> Result<(), BrokerError> {
        if !token(revoked) {
            return Err(BrokerError);
        }
        self.signer.verify(lease, revoked, None)?;
        self.neuron.revoke(revoked).await
    }

    fn handoff(&self, tokens: Tokens, scopes: Scopes) -> Result<Handoff, BrokerError> {
        let lease = self
            .signer
            .issue(&tokens.access, &tokens.refresh, &scopes.joined())?;
        Ok(Handoff {
            tokens,
            scopes,
            lease,
        })
    }
}

/// A pending authorization that is removed, with its local state released, unless Neuron's consent URL commits it.
struct AuthorizationGuard<'a> {
    broker: &'a Broker,
    broker_state: String,
    committed: bool,
}

impl AuthorizationGuard<'_> {
    fn commit(mut self) {
        self.committed = true;
    }
}

impl Drop for AuthorizationGuard<'_> {
    fn drop(&mut self) {
        if self.committed {
            return;
        }
        let mut state = self.broker.state();
        if let Some(removed) = state.authorizations.remove(&self.broker_state) {
            state.active.remove(&removed.local_state);
        }
    }
}

/// One reserved grant slot, freed with its local state released unless it becomes a stored grant.
struct ReservationGuard<'a> {
    broker: &'a Broker,
    local_state: String,
    armed: bool,
}

impl ReservationGuard<'_> {
    /// Store the exchanged tokens under a fresh claim in place of the reservation; the local state stays active.
    fn convert(mut self, now: Duration, pending: &PendingAuthorization, tokens: Tokens) -> String {
        let mut state = self.broker.state();
        state.expire(now);
        state.reservations -= 1;
        self.armed = false;
        let claim = unused(&|key| state.grants.contains_key(key), &mut random_claim);
        let token_expires_at =
            now + Duration::from_secs(u64::try_from(tokens.expires_in).unwrap_or_default());
        state.grants.insert(
            claim.clone(),
            PendingGrant {
                local_state: pending.local_state.clone(),
                challenge: pending.challenge.clone(),
                tokens,
                token_expires_at,
                scopes: pending.scopes.clone(),
                expires_at: now + GRANT_TTL,
            },
        );
        claim
    }
}

impl Drop for ReservationGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let mut state = self.broker.state();
            state.reservations -= 1;
            state.active.remove(&self.local_state);
        }
    }
}

/// A key `generate` yields that `taken` does not hold, drawing again on a collision.
fn unused(taken: &dyn Fn(&str) -> bool, generate: &mut dyn FnMut() -> String) -> String {
    loop {
        let candidate = generate();
        if !taken(&candidate) {
            return candidate;
        }
    }
}

fn random<const N: usize>() -> [u8; N] {
    let mut bytes = [0; N];
    getrandom::fill(&mut bytes).expect("the operating system's random source is available");
    bytes
}

/// `secrets.token_urlsafe(32)`: 43 base64url characters.
#[must_use]
pub fn random_binding() -> String {
    URL_SAFE_NO_PAD.encode(random::<32>())
}

/// `secrets.token_hex(32)`: 64 lowercase hexadecimal characters.
fn random_claim() -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    random::<32>()
        .iter()
        .flat_map(|byte| {
            [
                DIGITS[usize::from(byte >> 4)],
                DIGITS[usize::from(byte & 15)],
            ]
        })
        .map(char::from)
        .collect()
}

/// `secrets.token_urlsafe(18)`: a 24-character nonce.
#[must_use]
pub fn nonce() -> String {
    URL_SAFE_NO_PAD.encode(random::<18>())
}

/// The S256 PKCE challenge of a verifier.
#[must_use]
pub fn challenge_of(verifier: &str) -> String {
    URL_SAFE_NO_PAD.encode(Sha256::digest(verifier.as_bytes()))
}

#[cfg(test)]
mod tests;
