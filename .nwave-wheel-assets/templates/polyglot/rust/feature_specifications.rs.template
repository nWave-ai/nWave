//! feature_specifications.rs — step-function module backing the scenarios.
//!
//! Responsibilities:
//!   - Construct the SUT through the PRODUCTION composition root
//!     (`ProductionApp`). Swap only external / non-deterministic ports with
//!     fakes (clock, RNG, paid APIs).
//!   - Capture the universe via `app.capture_universe(...)`.
//!   - Assert via `assert_state_delta` from `common::state_delta`.
//!
//! No domain language leaks into the production-app wiring; no production-app
//! details leak into the scenarios.
//!
//! Rust idiom note: integration test files are per-file binaries; we share
//! per-scenario state via `thread_local!` cells so each step function can
//! mutate the SUT in turn. Cargo runs each `#[test]` on its own thread, so
//! the thread-locals are effectively per-test fixtures.

use std::cell::RefCell;
use std::collections::{BTreeMap, BTreeSet};

use serde_json::json;

use polyglot_pilot::common::state_delta::{
    appended_with, assert_state_delta, format_violations, unchanged, Expected, Snapshot,
    Universe,
};
use polyglot_pilot::production_app::ProductionApp;

// Universe for the signup feature — port-exposed observables only:
//   - "registry.users" : list of registered user records (driven-port state)
//   - "audit.events"   : append-only audit trail (driven-port state)
// Do NOT add internal fields here; refactoring would break the test.
const SIGNUP_UNIVERSE: &[&str] = &["registry.users", "audit.events"];

thread_local! {
    static APP: RefCell<Option<ProductionApp>> = const { RefCell::new(None) };
    static STATE_BEFORE: RefCell<Snapshot> = RefCell::new(BTreeMap::new());
}

fn universe_set() -> Universe {
    SIGNUP_UNIVERSE.iter().map(|k| (*k).to_string()).collect()
}

fn with_app<R>(f: impl FnOnce(&mut ProductionApp) -> R) -> R {
    APP.with(|cell| {
        let mut borrow = cell.borrow_mut();
        let app = borrow
            .as_mut()
            .expect("Given_* step must initialise ProductionApp first");
        f(app)
    })
}

fn capture_universe_now() -> Snapshot {
    APP.with(|cell| {
        let borrow = cell.borrow();
        let app = borrow
            .as_ref()
            .expect("Given_* step must initialise ProductionApp first");
        app.capture_universe(SIGNUP_UNIVERSE)
    })
}

// ---------------------------------------------------------------------------
// Step functions — Given / When / Then
// ---------------------------------------------------------------------------

pub fn given_a_fresh_signup_registry() {
    APP.with(|cell| *cell.borrow_mut() = Some(ProductionApp::new()));
    let baseline = capture_universe_now();
    STATE_BEFORE.with(|cell| *cell.borrow_mut() = baseline);
}

pub fn when_user_signs_up_with_email(email: &str) {
    with_app(|app| {
        let _ = app.signup(email);
    });
}

pub fn then_user_is_added_to_registry_and_audited_once(email: &str) {
    let after = capture_universe_now();
    let universe = universe_set();
    let mut expected: Expected = BTreeMap::new();
    expected.insert(
        "registry.users".to_string(),
        appended_with(json!({"email": email})),
    );
    expected.insert(
        "audit.events".to_string(),
        appended_with(json!({"type": "UserSignedUp", "email": email})),
    );

    STATE_BEFORE.with(|cell| {
        let before = cell.borrow();
        assert_state_delta(&*before, &after, &universe, &expected, false)
            .unwrap_or_else(|violations| panic!("{}", format_violations(&violations)));
    });
}

pub fn when_user_attempts_duplicate_signup(email: &str) {
    // Re-baseline before the duplicate attempt so the state-delta assertion
    // measures the change caused by the duplicate, not the original signup.
    let baseline = capture_universe_now();
    STATE_BEFORE.with(|cell| *cell.borrow_mut() = baseline);

    with_app(|app| {
        // Expected rejection — error swallowed here; the Then_ step asserts
        // the observable consequence (zero state delta).
        let _ = app.signup(email);
    });
}

pub fn then_second_signup_is_rejected_and_state_is_unchanged() {
    let after = capture_universe_now();
    let universe = universe_set();
    let mut expected: Expected = BTreeMap::new();
    expected.insert("registry.users".to_string(), unchanged());
    expected.insert("audit.events".to_string(), unchanged());

    STATE_BEFORE.with(|cell| {
        let before = cell.borrow();
        assert_state_delta(&*before, &after, &universe, &expected, false)
            .unwrap_or_else(|violations| panic!("{}", format_violations(&violations)));
    });
}

// Silence unused-import warnings when the BTreeSet path isn't yet used by a
// scenario in this template (kept for symmetry with other polyglot ports).
#[allow(dead_code)]
fn _unused_btreeset_anchor() -> BTreeSet<String> {
    BTreeSet::new()
}
