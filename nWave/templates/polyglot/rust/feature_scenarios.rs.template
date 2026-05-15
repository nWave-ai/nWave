//! feature_scenarios.rs — domain-language acceptance scenarios.
//!
//! Gojko Adzic Pillars 1+2:
//!   - Pillar 1: scenarios written in the domain language, no infrastructure
//!     noise.
//!   - Pillar 2: chained narrative — each scenario's Given may be the
//!     composition of the previous scenario's Given + When.
//!
//! Step functions (`given_*`, `when_*`, `then_*`) live in
//! `feature_specifications.rs`. This file contains NO direct asserts and NO
//! test-double wiring — those live in the specifications module.
//!
//! Place as `tests/feature_scenarios.rs` (Cargo integration test).

mod feature_specifications;

use feature_specifications::*;

#[test]
fn user_signs_up_with_valid_email_and_is_added_to_registry() {
    given_a_fresh_signup_registry();
    when_user_signs_up_with_email("alice@example.com");
    then_user_is_added_to_registry_and_audited_once("alice@example.com");
}

#[test]
fn duplicate_signup_is_rejected_and_leaves_state_unchanged() {
    // Pillar 2: this Given is the composition of the previous scenario's
    // Given + When — start with a registry already containing alice.
    given_a_fresh_signup_registry();
    when_user_signs_up_with_email("alice@example.com");

    when_user_attempts_duplicate_signup("alice@example.com");
    then_second_signup_is_rejected_and_state_is_unchanged();
}
