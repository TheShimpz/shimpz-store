//! The exact shapes of the broker's values, rule for rule as the Python broker's validators.

use strict_json::Value;

use super::{BrokerError, secret::printable};

/// Every scope the broker admits, in sorted order.
pub const ALLOWED_SCOPES: [&str; 4] = ["dns.read", "dns.write", "offline_access", "zone.read"];
/// The longest access or refresh token.
pub const MAX_TOKEN_BYTES: usize = 16 * 1024;
const BINDING_CHARS: usize = 43;

/// A non-empty, duplicate-free set of admitted scopes in sorted order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Scopes(Vec<&'static str>);

impl Scopes {
    /// Scopes given in sorted order without duplicates (`_scopes`).
    ///
    /// # Errors
    ///
    /// The list is empty, repeats or names an unknown scope, or is unsorted.
    pub fn sorted(items: &[&str]) -> Result<Self, BrokerError> {
        let scopes = Self::listed(items)?;
        let ordered = scopes.0.windows(2).all(|pair| pair[0] < pair[1]);
        ordered.then_some(scopes).ok_or(BrokerError)
    }

    /// Scopes a provider returned in any order, sorted (`_returned_scopes`).
    ///
    /// # Errors
    ///
    /// The list is empty, repeats, or names an unknown scope.
    pub fn returned(items: &[&str]) -> Result<Self, BrokerError> {
        let mut scopes = Self::listed(items)?;
        scopes.0.sort_unstable();
        Ok(scopes)
    }

    /// Scopes from a JSON array of strings given in sorted order.
    ///
    /// # Errors
    ///
    /// The value is not an array of strings, or its strings are not [`Scopes::sorted`].
    pub fn from_json(value: &Value) -> Result<Self, BrokerError> {
        let Value::Array(items) = value else {
            return Err(BrokerError);
        };
        let texts = items
            .iter()
            .map(|item| match item {
                Value::String(text) => Ok(text.as_str()),
                _ => Err(BrokerError),
            })
            .collect::<Result<Vec<_>, _>>()?;
        Self::sorted(&texts)
    }

    /// `_scope_list`: non-empty, unique, every scope admitted.
    fn listed(items: &[&str]) -> Result<Self, BrokerError> {
        let mut scopes = Vec::new();
        for item in items {
            let known = ALLOWED_SCOPES
                .iter()
                .find(|allowed| *allowed == item)
                .ok_or(BrokerError)?;
            if scopes.contains(known) {
                return Err(BrokerError);
            }
            scopes.push(*known);
        }
        if scopes.is_empty() {
            Err(BrokerError)
        } else {
            Ok(Self(scopes))
        }
    }

    /// The scopes in order.
    #[must_use]
    pub fn names(&self) -> &[&'static str] {
        &self.0
    }

    /// The scopes joined by one space.
    #[must_use]
    pub fn joined(&self) -> String {
        self.0.join(" ")
    }
}

/// A broker binding: exactly 43 base64url characters.
#[must_use]
pub fn binding(text: &str) -> bool {
    text.len() == BINDING_CHARS
        && text
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
}

/// Printable ASCII without a space, `minimum` to `maximum` bytes (`_code`).
#[must_use]
pub fn code(text: &str, minimum: usize, maximum: usize) -> bool {
    (minimum..=maximum).contains(&text.len()) && printable(text.as_bytes())
}

/// An access or refresh token: printable ASCII from 16 bytes to 16 KiB.
#[must_use]
pub fn token(text: &str) -> bool {
    code(text, 16, MAX_TOKEN_BYTES)
}

#[cfg(test)]
mod tests {
    use strict_json::Value;

    use super::{Scopes, binding, code, token};
    use crate::oauth::BrokerError;

    #[test]
    fn sorted_scopes_are_non_empty_unique_admitted_and_ordered() {
        let scopes = Scopes::sorted(&["dns.read", "zone.read"]).unwrap();
        assert_eq!(scopes.names(), ["dns.read", "zone.read"]);
        assert_eq!(scopes.joined(), "dns.read zone.read");
        let refused: [&[&str]; 5] = [
            &[],
            &["zone.read", "dns.read"],
            &["dns.read", "dns.read"],
            &["dns.read", "account.read"],
            &[""],
        ];
        for items in refused {
            assert_eq!(Scopes::sorted(items), Err(BrokerError), "{items:?}");
        }
    }

    #[test]
    fn caller_scopes_are_canonical_and_provider_scopes_stay_closed() {
        for refused in [&["dns.read", "dns.read"][..], &["dns.read", "unknown"]] {
            assert_eq!(Scopes::sorted(refused), Err(BrokerError));
            assert_eq!(Scopes::returned(refused), Err(BrokerError));
        }
        assert_eq!(Scopes::sorted(&["zone.read", "dns.read"]), Err(BrokerError));
        let scopes = Scopes::returned(&["zone.read", "offline_access", "dns.write"]).unwrap();
        assert_eq!(scopes.names(), ["dns.write", "offline_access", "zone.read"]);
        assert_eq!(
            Scopes::returned(&["zone.read", "zone.read"]),
            Err(BrokerError)
        );
        assert_eq!(Scopes::returned(&[]), Err(BrokerError));
    }

    #[test]
    fn json_scopes_are_an_array_of_sorted_strings() {
        let array = |items: Vec<Value>| Value::Array(items);
        let text = |text: &str| Value::String(text.to_owned());
        assert_eq!(
            Scopes::from_json(&array(vec![text("dns.read")])).map(|scopes| scopes.joined()),
            Ok("dns.read".to_owned())
        );
        for refused in [
            text("dns.read"),
            array(vec![Value::Null]),
            array(vec![text("zone.read"), text("dns.read")]),
        ] {
            assert_eq!(Scopes::from_json(&refused), Err(BrokerError), "{refused:?}");
        }
    }

    #[test]
    fn scalar_contracts_reject_invalid_values() {
        assert!(!code("short", 16, 4096));
        assert_eq!(Scopes::sorted(&[]), Err(BrokerError));
        assert!(binding(&"A_-9".repeat(11)[..43]));
        assert!(!binding(&"A".repeat(42)));
        assert!(!binding(&format!("{}=", "A".repeat(42))));
    }

    #[test]
    fn codes_and_tokens_are_printable_ascii_within_their_lengths() {
        assert!(code("abcdefgh", 8, 8));
        assert!(!code("abcdefg", 8, 9));
        assert!(!code("abcdefghij", 8, 9));
        assert!(!code("abcd efgh", 8, 9));
        assert!(token(&"t".repeat(16)));
        assert!(token(&"t".repeat(16 * 1024)));
        assert!(!token(&"t".repeat(16 * 1024 + 1)));
        assert!(!token("\u{e9}tttttttttttttttt"));
    }

    #[test]
    fn code_rejects_unencodable_text() {
        assert!(!code("authorization-code-\u{e9}", 16, 4096));
        assert!(!code(
            "\u{1f600}\u{1f600}\u{1f600}\u{1f600}\u{1f600}",
            16,
            4096
        ));
    }
}
