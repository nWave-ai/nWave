//! state_delta_test.rs — `#[cfg(test)]` contract tests for the Rust port.
//!
//! Mirrors `tests/state_delta/unit/test_matcher.py` and the predicate tests
//! for the Python canonical. Property-based assertions via `proptest!` where
//! the universe semantic is quantified (one PBT per predicate is the
//! layered-unit minimum).
//!
//! Place this file as `tests/state_delta_test.rs` (Cargo integration test)
//! or inline it inside a `#[cfg(test)] mod tests { ... }` block in the
//! library crate that owns `state_delta.rs`.

use std::collections::{BTreeMap, BTreeSet};

use proptest::prelude::*;
use serde_json::{json, Value};

// Adjust the path to match the crate that re-exports `state_delta`. For the
// pilot toy feature this is `polyglot_pilot::common::state_delta::*`.
use polyglot_pilot::common::state_delta::{
    appended_with, array_prepended, assert_state_delta, containing, format_violations,
    idempotent_after, legacy_healed, normalized_to, prepended_with, set_to, unchanged,
    Expected, Snapshot, Universe, ViolationKind,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn snap(pairs: &[(&str, Value)]) -> Snapshot {
    pairs.iter().map(|(k, v)| ((*k).to_string(), v.clone())).collect()
}

fn universe_of(keys: &[&str]) -> Universe {
    keys.iter().map(|k| (*k).to_string()).collect()
}

fn expected_of(pairs: Vec<(&str, polyglot_pilot::common::state_delta::Predicate)>) -> Expected {
    pairs.into_iter().map(|(k, p)| (k.to_string(), p)).collect()
}

// ---------------------------------------------------------------------------
// Walking skeleton + core semantics
// ---------------------------------------------------------------------------

#[test]
fn returns_ok_on_clean_prepend_transition() {
    let before = snap(&[("PATH", json!("/usr/bin"))]);
    let after = snap(&[("PATH", json!("/des/bin:/usr/bin"))]);
    let universe = universe_of(&["PATH"]);
    let expected = expected_of(vec![("PATH", prepended_with("/des/bin"))]);

    assert_state_delta(&before, &after, &universe, &expected, false)
        .expect("state-delta must pass");
}

#[test]
fn predicate_failure_returns_violation_with_full_context() {
    let before = snap(&[("PATH", json!("/usr/bin"))]);
    let after = snap(&[("PATH", json!("/wrong"))]);
    let universe = universe_of(&["PATH"]);
    let expected = expected_of(vec![("PATH", prepended_with("/des/bin"))]);

    let err = assert_state_delta(&before, &after, &universe, &expected, false)
        .expect_err("must record a violation");
    assert_eq!(err.len(), 1);
    let v = &err[0];
    assert_eq!(v.kind, ViolationKind::PredicateFailed);
    assert_eq!(v.key, "PATH");
    assert_eq!(v.old, json!("/usr/bin"));
    assert_eq!(v.new, json!("/wrong"));
    assert_eq!(v.predicate_name.as_deref(), Some("prepended_with(/des/bin)"));

    let msg = format_violations(&err);
    assert!(msg.contains("PATH"));
    assert!(msg.contains("prepended_with(/des/bin)"));
}

#[test]
fn implicit_unchanged_catches_undeclared_change() {
    let before = snap(&[("PATH", json!("/u/bin")), ("HOME", json!("/home/u"))]);
    let after = snap(&[
        ("PATH", json!("/des/bin:/u/bin")),
        ("HOME", json!("/home/changed")),
    ]);
    let universe = universe_of(&["PATH", "HOME"]);
    let expected = expected_of(vec![("PATH", prepended_with("/des/bin"))]);

    let err = assert_state_delta(&before, &after, &universe, &expected, false)
        .expect_err("must record HOME drift");
    assert_eq!(err.len(), 1);
    assert_eq!(err[0].kind, ViolationKind::UndeclaredChange);
    assert_eq!(err[0].key, "HOME");
}

#[test]
fn collects_multiple_violations_a7() {
    let before = snap(&[("PATH", json!("/u")), ("HOME", json!("/h")), ("X", json!("1"))]);
    let after = snap(&[("PATH", json!("/wrong")), ("HOME", json!("/h2")), ("X", json!("1"))]);
    let universe = universe_of(&["PATH", "HOME", "X"]);
    let expected = expected_of(vec![
        ("PATH", prepended_with("/des")),
        ("HOME", unchanged()),
    ]);

    let err = assert_state_delta(&before, &after, &universe, &expected, false)
        .expect_err("must record two violations");
    assert_eq!(err.len(), 2);
    let mut keys: Vec<&str> = err.iter().map(|v| v.key.as_str()).collect();
    keys.sort();
    assert_eq!(keys, vec!["HOME", "PATH"]);
}

#[test]
fn strict_mode_flags_keys_not_in_universe() {
    let before = snap(&[("PATH", json!("/u")), ("EXTRA", json!("x"))]);
    let after = snap(&[("PATH", json!("/des:/u")), ("EXTRA", json!("x2"))]);
    let universe = universe_of(&["PATH"]);
    let expected = expected_of(vec![("PATH", prepended_with("/des"))]);

    let err = assert_state_delta(&before, &after, &universe, &expected, true)
        .expect_err("must flag EXTRA as strict mismatch");
    assert!(err.iter().any(|v| {
        v.kind == ViolationKind::StrictUniverseMismatch && v.key == "EXTRA"
    }));
}

// ---------------------------------------------------------------------------
// Predicate library — Python parity
// ---------------------------------------------------------------------------

#[test]
fn unchanged_passes_iff_deep_equal() {
    let p = unchanged();
    assert!(p.call(&json!(1), &json!(1)).ok);
    assert!(!p.call(&json!(1), &json!(2)).ok);
    assert!(p.call(&json!({"a": 1}), &json!({"a": 1})).ok);
    assert!(!p.call(&json!({"a": 1}), &json!({"a": 2})).ok);
}

#[test]
fn prepended_with_passes_when_prefix_plus_sep_plus_old() {
    let p = prepended_with("/des/bin");
    assert!(p.call(&json!("/usr/bin"), &json!("/des/bin:/usr/bin")).ok);
    assert!(!p.call(&json!("/usr/bin"), &json!("/wrong")).ok);
}

#[test]
fn appended_with_str_passes_when_old_plus_sep_plus_suffix() {
    use polyglot_pilot::common::state_delta::appended_with_str;
    let p = appended_with_str(".bak");
    assert!(p.call(&json!("/etc/hosts"), &json!("/etc/hosts:.bak")).ok);
    assert!(!p.call(&json!("/etc/hosts"), &json!("/etc/hosts")).ok);
}

#[test]
fn set_to_ignores_old_and_matches_new() {
    let p = set_to(json!("active"));
    assert!(p.call(&json!("inactive"), &json!("active")).ok);
    assert!(p.call(&json!("anything"), &json!("active")).ok);
    assert!(!p.call(&json!("inactive"), &json!("pending")).ok);
}

#[test]
fn containing_checks_substring_or_array_element() {
    assert!(containing(json!("/usr/bin")).call(&json!(""), &json!("/des/bin:/usr/bin")).ok);
    assert!(!containing(json!("/usr/bin")).call(&json!(""), &json!("/des/bin:/opt/bin")).ok);
    assert!(containing(json!({"id": 1})).call(&Value::Null, &json!([{"id": 1}, {"id": 2}])).ok);
    assert!(!containing(json!({"id": 9})).call(&Value::Null, &json!([{"id": 1}, {"id": 2}])).ok);
}

#[test]
fn normalized_to_compares_under_normaliser() {
    let p = normalized_to(|v: &Value| match v {
        Value::String(s) => Value::String(s.replace("$HOME", "/home/u")),
        other => other.clone(),
    });
    assert!(p.call(&json!("/home/u/.local/bin"), &json!("$HOME/.local/bin")).ok);
    assert!(!p.call(&json!("/home/u/.local/bin"), &json!("$HOME/.other/bin")).ok);
}

#[test]
fn idempotent_after_checks_first_segment() {
    let p = idempotent_after("DES_BIN");
    assert!(p.call(&json!("anything"), &json!("DES_BIN:/usr/bin")).ok);
    assert!(!p.call(&json!("anything"), &json!("/usr/bin:/opt/bin")).ok);
}

#[test]
fn legacy_healed_implements_paper_trace() {
    const LEGACY: &str = "DES_BIN:SYSTEM_PATH_FALLBACK";
    let p = legacy_healed(
        |v| matches!(v, Value::String(s) if s == LEGACY),
        |v| matches!(v, Value::String(s) if s != LEGACY && s.starts_with("DES_BIN:")),
    );
    assert!(p.call(&json!(LEGACY), &json!("DES_BIN:/usr/bin")).ok);
    assert!(!p.call(&json!(LEGACY), &json!(LEGACY)).ok);
    assert!(!p.call(&json!("/usr/bin"), &json!("DES_BIN:/usr/bin")).ok);
}

#[test]
fn array_prepended_matches_head_insert() {
    assert!(array_prepended(json!("a")).call(&json!([]), &json!(["a"])).ok);
    assert!(array_prepended(json!("a")).call(&json!(["x"]), &json!(["a", "x"])).ok);
    assert!(!array_prepended(json!("a")).call(&json!(["x"]), &json!(["x", "a"])).ok);
    assert!(!array_prepended(json!("a")).call(&json!(["x"]), &json!(["a"])).ok);
}

#[test]
fn appended_with_matches_tail_insert() {
    assert!(appended_with(json!("z")).call(&json!([]), &json!(["z"])).ok);
    assert!(appended_with(json!("z")).call(&json!(["x"]), &json!(["x", "z"])).ok);
    assert!(!appended_with(json!("z")).call(&json!(["x"]), &json!(["z", "x"])).ok);
}

// ---------------------------------------------------------------------------
// Property-based tests — universe semantics
// ---------------------------------------------------------------------------

proptest! {
    /// `unchanged()` always passes on identical operands.
    #[test]
    fn pbt_unchanged_reflexive(s in any::<String>()) {
        let v = Value::String(s);
        prop_assert!(unchanged().call(&v, &v).ok);
    }

    /// `prepended_with("PRE")` accepts any tail composed as `PRE:{tail}`.
    #[test]
    fn pbt_prepended_with_composes(tail in any::<String>()) {
        let composed = format!("PRE:{}", tail);
        prop_assert!(prepended_with("PRE")
            .call(&Value::String(tail), &Value::String(composed))
            .ok);
    }

    /// Implicit-unchanged: any disagreement on an adjacent slot triggers a
    /// violation, regardless of the values.
    #[test]
    fn pbt_implicit_unchanged_forbids_hidden_mutation(
        old_home in "[a-z]+", new_home in "[a-z]+",
    ) {
        prop_assume!(old_home != new_home);
        let before = snap(&[("PATH", json!("/u")), ("HOME", json!(old_home))]);
        let after = snap(&[("PATH", json!("/des:/u")), ("HOME", json!(new_home))]);
        let universe = universe_of(&["PATH", "HOME"]);
        let expected = expected_of(vec![("PATH", prepended_with("/des"))]);
        let result = assert_state_delta(&before, &after, &universe, &expected, false);
        prop_assert!(result.is_err());
    }
}

#[test]
fn permits_mutation_only_on_slots_with_matching_predicates() {
    let before = snap(&[("PATH", json!("/u")), ("HOME", json!("/h"))]);
    let after = snap(&[("PATH", json!("/des:/u")), ("HOME", json!("/h"))]);
    let universe = universe_of(&["PATH", "HOME"]);
    let expected = expected_of(vec![("PATH", prepended_with("/des"))]);
    assert_state_delta(&before, &after, &universe, &expected, false).expect("must pass");
}
