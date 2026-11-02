// feature_scenarios_test.go — domain-language acceptance scenarios.
//
// Gojko Adzic Pillars 1+2:
//   - Pillar 1: scenarios written in the domain language, no infrastructure noise
//   - Pillar 2: chained narrative — each scenario's Given may be the
//               composition of the previous scenario's Given + When
//
// Step functions (given_*, when_*, then_*) are defined in
// `feature_specifications_test.go`. This file contains NO direct asserts and
// NO test-double wiring — those live in the specifications module.
//
// Production composition (Tier A): step functions construct the SUT through
// the real composition root and swap only external / non-deterministic ports
// with fakes. State-delta assertions go through the project's `common/statedelta`
// package.

package feature_test

import "testing"

func TestSignup_UserAddedToRegistry(t *testing.T) {
	given_a_fresh_signup_registry(t)
	when_user_signs_up_with_email(t, "alice@example.com")
	then_user_is_added_to_registry_and_audited_once(t, "alice@example.com")
}

func TestSignup_DuplicateRejected(t *testing.T) {
	// Pillar 2: this Given is the composition of the previous scenario's
	// Given + When — start with a registry already containing alice.
	given_a_fresh_signup_registry(t)
	when_user_signs_up_with_email(t, "alice@example.com")

	when_user_attempts_duplicate_signup(t, "alice@example.com")
	then_second_signup_is_rejected_and_state_is_unchanged(t)
}
