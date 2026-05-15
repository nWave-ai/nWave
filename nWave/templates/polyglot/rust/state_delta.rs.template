//! state_delta.rs — Rust port of nwave_ai.state_delta (Python canonical).
//!
//! Polyglot pilot (Epic 3). Mirrors the contract of
//! `nwave_ai/state_delta/{matcher,predicates}.py`:
//!
//!   - Predicate signature: `Fn(&Value, &Value) -> PredicateResult`
//!   - Universe = `BTreeSet<String>` (set semantics; duplicates ignored)
//!   - `assert_state_delta` collects ALL violations across the universe before
//!     returning a single `Err(Vec<StateDeltaViolation>)` aggregating them
//!     (multi-violation contract A7).
//!   - Strict mode reports any key present in before|after but not in universe
//!     as a `StrictUniverseMismatch` violation.
//!   - Implicit-unchanged: a key in universe but NOT in expected requires
//!     deep-equal between `before[key]` and `after[key]`; difference =>
//!     `UndeclaredChange` violation.
//!
//! Dependencies: `serde_json` for `Value` (deep-equality is native via
//! `PartialEq`) — keeps the file drop-in friendly for any Rust project.
//! Library code returns `Result<>`; panics are reserved for test code.
//!
//! Source of truth: Python module at `nwave_ai/state_delta/`. Keep the
//! contract in sync; deviations are bugs.
//!
//! Cargo.toml companion:
//!     [dependencies]
//!     serde_json = "1"
//!     [dev-dependencies]
//!     proptest = "1.4"

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::sync::Arc;

use serde_json::Value;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// A snapshot of universe slots. Keys are slot names; values are JSON-shaped.
pub type Snapshot = BTreeMap<String, Value>;

/// Universe — set of slot names under observation.
pub type Universe = BTreeSet<String>;

/// Outcome of a predicate evaluation: `ok=true` passes; `ok=false` carries a
/// human-readable reason that surfaces in the violation message.
#[derive(Debug, Clone)]
pub struct PredicateResult {
    pub ok: bool,
    pub reason: String,
}

impl PredicateResult {
    pub fn pass() -> Self {
        Self {
            ok: true,
            reason: String::new(),
        }
    }
    pub fn fail<R: Into<String>>(reason: R) -> Self {
        Self {
            ok: false,
            reason: reason.into(),
        }
    }
}

/// Predicate function signature. Stored boxed + `Arc` so the same predicate
/// can be cloned across slots and threads (`Send + Sync`).
type PredicateFn = dyn Fn(&Value, &Value) -> PredicateResult + Send + Sync;

/// A named predicate. The `name` is what shows up in violation messages, so
/// keep it short and parameter-bearing (e.g. `"prepended_with(/des/bin)"`).
#[derive(Clone)]
pub struct Predicate {
    pub name: String,
    pub func: Arc<PredicateFn>,
}

impl Predicate {
    pub fn new<N, F>(name: N, func: F) -> Self
    where
        N: Into<String>,
        F: Fn(&Value, &Value) -> PredicateResult + Send + Sync + 'static,
    {
        Self {
            name: name.into(),
            func: Arc::new(func),
        }
    }

    pub fn call(&self, old: &Value, new: &Value) -> PredicateResult {
        (self.func)(old, new)
    }
}

impl fmt::Debug for Predicate {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Predicate").field("name", &self.name).finish()
    }
}

/// Map of expected per-slot predicates.
pub type Expected = BTreeMap<String, Predicate>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ViolationKind {
    UndeclaredChange,
    PredicateFailed,
    StrictUniverseMismatch,
}

impl fmt::Display for ViolationKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            ViolationKind::UndeclaredChange => "undeclared_change",
            ViolationKind::PredicateFailed => "predicate_failed",
            ViolationKind::StrictUniverseMismatch => "strict_universe_mismatch",
        };
        f.write_str(s)
    }
}

#[derive(Debug, Clone)]
pub struct StateDeltaViolation {
    pub kind: ViolationKind,
    pub key: String,
    pub old: Value,
    pub new: Value,
    /// Present iff `kind == PredicateFailed`.
    pub predicate_name: Option<String>,
    /// Predicate-supplied reason; empty when not applicable.
    pub reason: String,
}

impl fmt::Display for StateDeltaViolation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "  kind='{}' key='{}' old={} new={}",
            self.kind, self.key, self.old, self.new
        )?;
        if let Some(name) = &self.predicate_name {
            write!(f, " predicate_name='{}'", name)?;
        }
        if !self.reason.is_empty() {
            write!(f, " reason='{}'", self.reason)?;
        }
        Ok(())
    }
}

/// Format a collection of violations into the canonical multi-line message.
pub fn format_violations(violations: &[StateDeltaViolation]) -> String {
    let mut out = format!(
        "assert_state_delta: {} violation(s) detected:",
        violations.len()
    );
    for v in violations {
        out.push('\n');
        out.push_str(&v.to_string());
    }
    out
}

// ---------------------------------------------------------------------------
// Predicate factories — mirror nwave_ai/state_delta/predicates.py
// ---------------------------------------------------------------------------

/// Passes when `old` equals `new` (deep equality via `serde_json::Value`).
pub fn unchanged() -> Predicate {
    Predicate::new("unchanged()", |old, new| {
        if old == new {
            PredicateResult::pass()
        } else {
            PredicateResult::fail("values differ")
        }
    })
}

/// Passes when `new` is a string `prefix + sep + old`. PATH-style composition.
pub fn prepended_with(prefix: impl Into<String>) -> Predicate {
    prepended_with_sep(prefix, ":")
}

pub fn prepended_with_sep(prefix: impl Into<String>, sep: impl Into<String>) -> Predicate {
    let prefix = prefix.into();
    let sep = sep.into();
    let expected_prefix = format!("{}{}", prefix, sep);
    let name = format!("prepended_with({})", prefix);
    Predicate::new(name, move |old, new| match (old.as_str(), new.as_str()) {
        (Some(o), Some(n)) => {
            if n == format!("{}{}", expected_prefix, o) {
                PredicateResult::pass()
            } else {
                PredicateResult::fail("new is not prefix+sep+old")
            }
        }
        _ => PredicateResult::fail("non-string operand"),
    })
}

/// Passes when `new` is a string `old + sep + suffix`.
pub fn appended_with_str(suffix: impl Into<String>) -> Predicate {
    appended_with_sep(suffix, ":")
}

pub fn appended_with_sep(suffix: impl Into<String>, sep: impl Into<String>) -> Predicate {
    let suffix = suffix.into();
    let sep = sep.into();
    let name = format!("appended_with({})", suffix);
    Predicate::new(name, move |old, new| match (old.as_str(), new.as_str()) {
        (Some(o), Some(n)) => {
            if n == format!("{}{}{}", o, sep, suffix) {
                PredicateResult::pass()
            } else {
                PredicateResult::fail("new is not old+sep+suffix")
            }
        }
        _ => PredicateResult::fail("non-string operand"),
    })
}

/// Passes when `new` deep-equals `value` (old is ignored).
pub fn set_to(value: Value) -> Predicate {
    let name = format!("set_to({})", value);
    let captured = value.clone();
    Predicate::new(name, move |_old, new| {
        if *new == captured {
            PredicateResult::pass()
        } else {
            PredicateResult::fail("new != expected value")
        }
    })
}

/// Passes when `substring` is a substring of `new` (string) OR when `new` is
/// a JSON array that includes a deep-equal element to `substring`.
pub fn containing(substring: Value) -> Predicate {
    let name = format!("containing({})", substring);
    let captured = substring.clone();
    Predicate::new(name, move |_old, new| match (&captured, new) {
        (Value::String(s), Value::String(n)) => {
            if n.contains(s.as_str()) {
                PredicateResult::pass()
            } else {
                PredicateResult::fail("substring not found")
            }
        }
        (_, Value::Array(arr)) => {
            if arr.iter().any(|el| el == &captured) {
                PredicateResult::pass()
            } else {
                PredicateResult::fail("element not present in array")
            }
        }
        _ => PredicateResult::fail("incompatible operand shapes"),
    })
}

/// Passes when `normalizer(old) == normalizer(new)`.
pub fn normalized_to<F>(normalizer: F) -> Predicate
where
    F: Fn(&Value) -> Value + Send + Sync + 'static,
{
    let normalizer = Arc::new(normalizer);
    Predicate::new("normalized_to(<normalizer>)", move |old, new| {
        if normalizer(old) == normalizer(new) {
            PredicateResult::pass()
        } else {
            PredicateResult::fail("normalized forms differ")
        }
    })
}

/// Passes when the first segment of `new` (split by `sep`) equals `prefix`.
/// Used to assert a prepend-if-absent operation left the slot untouched
/// because the prefix was already present.
pub fn idempotent_after(prefix: impl Into<String>) -> Predicate {
    idempotent_after_sep(prefix, ":")
}

pub fn idempotent_after_sep(prefix: impl Into<String>, sep: impl Into<String>) -> Predicate {
    let prefix = prefix.into();
    let sep = sep.into();
    let name = format!("idempotent_after({})", prefix);
    Predicate::new(name, move |_old, new| match new.as_str() {
        Some(n) => {
            let first = n.split(sep.as_str()).next().unwrap_or("");
            if first == prefix {
                PredicateResult::pass()
            } else {
                PredicateResult::fail("first segment != prefix")
            }
        }
        None => PredicateResult::fail("non-string operand"),
    })
}

/// Passes when `detector(old)` AND `healed_check(new)` are both true.
/// Paper-trace for migrating fabricated legacy values to a healed shape.
pub fn legacy_healed<D, H>(detector: D, healed_check: H) -> Predicate
where
    D: Fn(&Value) -> bool + Send + Sync + 'static,
    H: Fn(&Value) -> bool + Send + Sync + 'static,
{
    let detector = Arc::new(detector);
    let healed_check = Arc::new(healed_check);
    Predicate::new("legacy_healed(<det>,<heal>)", move |old, new| {
        if detector(old) && healed_check(new) {
            PredicateResult::pass()
        } else {
            PredicateResult::fail("legacy not detected or new not healed")
        }
    })
}

// ---------------------------------------------------------------------------
// Array-shaped helpers (Rust extension — beyond Python parity)
// ---------------------------------------------------------------------------

/// Passes when `new` is `[item, ...old]` (JSON array prepend).
pub fn array_prepended(item: Value) -> Predicate {
    let name = format!("array_prepended({})", item);
    Predicate::new(name, move |old, new| match (old, new) {
        (Value::Array(o), Value::Array(n)) => {
            if n.len() != o.len() + 1 {
                return PredicateResult::fail("length mismatch");
            }
            if n[0] != item {
                return PredicateResult::fail("first element != item");
            }
            for i in 0..o.len() {
                if n[i + 1] != o[i] {
                    return PredicateResult::fail("tail diverged from old");
                }
            }
            PredicateResult::pass()
        }
        _ => PredicateResult::fail("non-array operand"),
    })
}

/// Passes when `new` is `[...old, item]` (JSON array append).
pub fn appended_with(item: Value) -> Predicate {
    let name = format!("appended_with({})", item);
    Predicate::new(name, move |old, new| match (old, new) {
        (Value::Array(o), Value::Array(n)) => {
            if n.len() != o.len() + 1 {
                return PredicateResult::fail("length mismatch");
            }
            if n[n.len() - 1] != item {
                return PredicateResult::fail("last element != item");
            }
            for i in 0..o.len() {
                if n[i] != o[i] {
                    return PredicateResult::fail("prefix diverged from old");
                }
            }
            PredicateResult::pass()
        }
        _ => PredicateResult::fail("non-array operand"),
    })
}

// ---------------------------------------------------------------------------
// Driving function — assert_state_delta
// ---------------------------------------------------------------------------

/// Assert that state transitions satisfy the expected predicates.
///
/// For each key in `universe`:
///   - If the key has a predicate in `expected`, the predicate is called with
///     `(before[key], after[key])`. A failing result records a
///     `PredicateFailed` violation.
///   - If the key is NOT in `expected`, `before[key]` must deep-equal
///     `after[key]`. A difference records an `UndeclaredChange` violation
///     (implicit-unchanged enforcement).
///
/// Strict mode: any key present in `before` or `after` but not in `universe`
/// records a `StrictUniverseMismatch` violation.
///
/// All violations are collected across the full universe before a single
/// `Err(Vec<StateDeltaViolation>)` is returned (multi-violation contract A7).
pub fn assert_state_delta(
    before: &Snapshot,
    after: &Snapshot,
    universe: &Universe,
    expected: &Expected,
    strict: bool,
) -> Result<(), Vec<StateDeltaViolation>> {
    let mut violations: Vec<StateDeltaViolation> = Vec::new();

    if strict {
        let mut seen: BTreeSet<&String> = BTreeSet::new();
        seen.extend(before.keys());
        seen.extend(after.keys());
        for key in seen {
            if !universe.contains(key) {
                violations.push(StateDeltaViolation {
                    kind: ViolationKind::StrictUniverseMismatch,
                    key: key.clone(),
                    old: before.get(key).cloned().unwrap_or(Value::Null),
                    new: after.get(key).cloned().unwrap_or(Value::Null),
                    predicate_name: None,
                    reason: String::new(),
                });
            }
        }
    }

    for key in universe {
        let old = before.get(key).cloned().unwrap_or(Value::Null);
        let new = after.get(key).cloned().unwrap_or(Value::Null);
        match expected.get(key) {
            Some(predicate) => {
                let result = predicate.call(&old, &new);
                if !result.ok {
                    violations.push(StateDeltaViolation {
                        kind: ViolationKind::PredicateFailed,
                        key: key.clone(),
                        old,
                        new,
                        predicate_name: Some(predicate.name.clone()),
                        reason: result.reason,
                    });
                }
            }
            None => {
                if old != new {
                    violations.push(StateDeltaViolation {
                        kind: ViolationKind::UndeclaredChange,
                        key: key.clone(),
                        old,
                        new,
                        predicate_name: None,
                        reason: String::new(),
                    });
                }
            }
        }
    }

    if violations.is_empty() {
        Ok(())
    } else {
        Err(violations)
    }
}

// NWAVE-POLYGLOT-RUST v1 — pilot template. Python canonical source of truth
// lives at `nwave_ai/state_delta/`. Updates to the Python contract must be
// ported here.
