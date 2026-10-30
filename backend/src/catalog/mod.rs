//! The public Assistant catalog and icon routes: the locale must be exactly one closed `locale=` query; a served
//! catalog says how old it is so no cache after Store keeps it past its lifetime; every refusal is uncached.

pub mod cache;
pub mod icons;
pub mod project;
pub mod upstream;

#[cfg(test)]
mod testing;

use std::{sync::Arc, time::Duration};

use http::{HeaderName, HeaderValue, StatusCode, header};
use team_protocol::payload::{CHAT_LOCALES, SHA256_RE};

use crate::{clock::Clock, response::Reply, static_files::IMMUTABLE_CACHE};

use self::{cache::Catalogs, icons::Icons, upstream::Developers};

const CATALOG_CACHE: &str = "public, max-age=60, s-maxage=300";

/// The catalog and icon reads one Store shares.
pub struct Catalog {
    catalogs: Arc<Catalogs>,
    icons: Arc<Icons>,
}

impl Catalog {
    /// Catalogs and icons read from `developers`, waiting at most `slot_wait` for one of its load slots.
    #[must_use]
    pub fn new(developers: &Developers, clock: Arc<dyn Clock>, slot_wait: Duration) -> Self {
        Self {
            catalogs: Arc::new(Catalogs::new(developers.clone(), clock, slot_wait)),
            icons: Arc::new(Icons::new(developers.clone(), slot_wait)),
        }
    }

    /// `GET /api/assistants` with this raw query.
    pub async fn catalog(&self, query: Option<&str>) -> Reply {
        let Some(locale) = locale(query) else {
            return uncached(
                StatusCode::BAD_REQUEST,
                "Assistant catalog locale is invalid",
            );
        };
        let Some((read_at, body)) = self.catalogs.served(locale).await else {
            return uncached(
                StatusCode::SERVICE_UNAVAILABLE,
                "Assistant catalog is unavailable",
            );
        };
        let age = self.catalogs.now().saturating_sub(read_at).as_secs();
        Reply::json(
            StatusCode::OK,
            body,
            vec![
                (
                    header::CACHE_CONTROL,
                    HeaderValue::from_static(CATALOG_CACHE),
                ),
                (header::AGE, HeaderValue::from(age)),
            ],
        )
    }

    /// `GET /api/assistant-icons/{source}/{icon}.png`.
    pub async fn icon(&self, source: &str, icon: &str) -> Reply {
        let unavailable = || {
            uncached(
                StatusCode::SERVICE_UNAVAILABLE,
                "Assistant icon is unavailable",
            )
        };
        if !SHA256_RE.is_full(source) || !SHA256_RE.is_full(icon) {
            return unavailable();
        }
        let Some(contents) = self.icons.icon(source, icon).await else {
            return unavailable();
        };
        let nosniff: (HeaderName, HeaderValue) = (
            header::X_CONTENT_TYPE_OPTIONS,
            HeaderValue::from_static("nosniff"),
        );
        Reply::new(
            StatusCode::OK,
            vec![
                (
                    header::CACHE_CONTROL,
                    HeaderValue::from_static(IMMUTABLE_CACHE),
                ),
                nosniff,
            ],
            Some("image/png"),
            contents,
        )
    }
}

/// The one closed locale a raw query names as exactly `locale=<code>`.
#[must_use]
pub fn locale(query: Option<&str>) -> Option<&'static str> {
    let requested = query?.strip_prefix("locale=")?;
    CHAT_LOCALES
        .iter()
        .copied()
        .find(|known| *known == requested)
}

fn uncached(status: StatusCode, detail: &str) -> Reply {
    Reply::detail(
        status,
        detail,
        vec![(header::CACHE_CONTROL, HeaderValue::from_static("no-store"))],
    )
}

#[cfg(test)]
mod tests;
