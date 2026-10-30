//! Civil dates from Unix time, without a date crate: the log's RFC 3339 timestamps and HTTP's IMF-fixdate.
//!
//! Days convert to a proleptic Gregorian date with Howard Hinnant's `civil_from_days` over `i64`, valid for every
//! sign; 1970-01-01 was a Thursday.

use std::time::Duration;

const SECONDS_PER_DAY: i64 = 86_400;
/// The last second IMF-fixdate's four-digit years can name: 9999-12-31T23:59:59Z.
pub const LAST_IMF_SECOND: i64 = 253_402_300_799;
const WEEKDAYS: [&str; 7] = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"];
const MONTHS: [&str; 12] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/// The proleptic Gregorian year, month (1-12), and day (1-31) of a day count since 1970-01-01.
#[must_use]
pub fn civil(days: i64) -> (i64, i64, i64) {
    let shifted = days + 719_468;
    let era = shifted.div_euclid(146_097);
    let of_era = shifted.rem_euclid(146_097);
    let year_of_era = (of_era - of_era / 1_460 + of_era / 36_524 - of_era / 146_096) / 365;
    let day_of_year = of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let shifted_month = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * shifted_month + 2) / 5 + 1;
    let month = if shifted_month < 10 {
        shifted_month + 3
    } else {
        shifted_month - 9
    };
    let year = year_of_era + era * 400 + i64::from(month <= 2);
    (year, month, day)
}

/// `YYYY-MM-DDTHH:MM:SS.ffffffZ` for a time after the epoch, microseconds truncated.
#[must_use]
pub fn rfc3339_micros(since_epoch: Duration) -> String {
    let seconds = i64::try_from(since_epoch.as_secs()).unwrap_or(i64::MAX);
    let (year, month, day) = civil(seconds.div_euclid(SECONDS_PER_DAY));
    let of_day = seconds.rem_euclid(SECONDS_PER_DAY);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}.{:06}Z",
        of_day / 3_600,
        of_day / 60 % 60,
        of_day % 60,
        since_epoch.subsec_micros()
    )
}

/// `Tue, 14 Nov 2023 22:13:20 GMT` for a whole Unix second from 1970 through 9999; `None` outside them.
#[must_use]
pub fn imf_fixdate(seconds: i64) -> Option<String> {
    if !(0..=LAST_IMF_SECOND).contains(&seconds) {
        return None;
    }
    let days = seconds / SECONDS_PER_DAY;
    let (year, month, day) = civil(days);
    let of_day = seconds % SECONDS_PER_DAY;
    let weekday = WEEKDAYS[usize::try_from(days % 7).unwrap_or_default()];
    let month_name = MONTHS[usize::try_from(month - 1).unwrap_or_default()];
    Some(format!(
        "{weekday}, {day:02} {month_name} {year:04} {:02}:{:02}:{:02} GMT",
        of_day / 3_600,
        of_day / 60 % 60,
        of_day % 60
    ))
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use super::{LAST_IMF_SECOND, civil, imf_fixdate, rfc3339_micros};

    #[test]
    fn civil_dates_hold_on_both_sides_of_the_epoch_and_across_leap_rules() {
        assert_eq!(civil(0), (1970, 1, 1));
        assert_eq!(civil(-1), (1969, 12, 31));
        assert_eq!(civil(11_016), (2000, 2, 29));
        assert_eq!(civil(-25_508), (1900, 3, 1));
        assert_eq!(civil(-25_509), (1900, 2, 28));
        assert_eq!(civil(-719_528), (0, 1, 1));
        assert_eq!(civil(2_932_896), (9999, 12, 31));
    }

    #[test]
    fn imf_fixdate_names_every_second_of_four_digit_years_and_nothing_else() {
        assert_eq!(
            imf_fixdate(1_700_000_000).as_deref(),
            Some("Tue, 14 Nov 2023 22:13:20 GMT")
        );
        assert_eq!(
            imf_fixdate(1_700_000_001).as_deref(),
            Some("Tue, 14 Nov 2023 22:13:21 GMT")
        );
        assert_eq!(
            imf_fixdate(0).as_deref(),
            Some("Thu, 01 Jan 1970 00:00:00 GMT")
        );
        assert_eq!(
            imf_fixdate(LAST_IMF_SECOND).as_deref(),
            Some("Fri, 31 Dec 9999 23:59:59 GMT")
        );
        assert_eq!(
            imf_fixdate(951_782_400).as_deref(),
            Some("Tue, 29 Feb 2000 00:00:00 GMT")
        );
        for outside in [-1, LAST_IMF_SECOND + 1, i64::MIN, i64::MAX] {
            assert_eq!(imf_fixdate(outside), None, "{outside}");
        }
    }

    #[test]
    fn log_timestamps_carry_microseconds() {
        assert_eq!(
            rfc3339_micros(Duration::new(1_700_000_000, 383_159_999)),
            "2023-11-14T22:13:20.383159Z"
        );
        assert_eq!(
            rfc3339_micros(Duration::ZERO),
            "1970-01-01T00:00:00.000000Z"
        );
    }
}
