//! The Rust side of `oracle/differential.py`: reads cases framed as a 4-byte big-endian length and JSON from stdin and
//! writes one canonical answer per case. Its one argument is the oracle's work directory, holding the build.

#[path = "../tests/support/decide.rs"]
mod decide;

use std::io::{self, BufWriter, Read, Write};

fn main() -> io::Result<()> {
    let work = std::env::args_os().nth(1).expect("the work directory");
    let decider = decide::Decider::new(std::path::Path::new(&work));
    let mut input = Vec::new();
    io::stdin().lock().read_to_end(&mut input)?;
    let mut output = BufWriter::new(io::stdout().lock());
    let mut rest = input.as_slice();
    while let Some((length, after)) = rest.split_first_chunk::<4>() {
        let (case, after) =
            after.split_at(usize::try_from(u32::from_be_bytes(*length)).expect("u32 fits usize"));
        let case = strict_json::parse(case).expect("the oracle writes JSON cases");
        writeln!(output, "{}", decider.decide(&case))?;
        rest = after;
    }
    assert!(rest.is_empty(), "the input ends inside a frame");
    output.flush()
}
