//! polyglot_pilot — minimal toy crate exercising the Rust state-delta port.
//!
//! Modules:
//!   - `common::state_delta` — copy of the port template (R.1).
//!   - `production_app`     — toy ProductionApp with signup feature.
//!
//! Integration tests under `tests/` import these via the crate name
//! `polyglot_pilot`.

pub mod common;
pub mod production_app;

pub use production_app::{DuplicateSignupError, ProductionApp};
