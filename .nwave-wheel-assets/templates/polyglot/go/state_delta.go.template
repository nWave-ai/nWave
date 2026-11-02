// Package statedelta — Go port of nwave_ai.state_delta (Python canonical).
//
// Polyglot pilot (Epic 3 — Go). Mirrors the contract of
// `nwave_ai/state_delta/{matcher,predicates}.py`:
//
//   - Predicate signature: func(oldValue, newValue interface{}) PredicateResult
//   - Universe = []string (set semantics; duplicates ignored)
//   - AssertStateDelta collects ALL violations across the universe before
//     surfacing a single aggregated failure via testing.T (multi-violation
//     contract A7). Calls t.Errorf for each violation, then t.FailNow once
//     so the test fails atomically with the full violation context.
//   - Strict mode reports any key present in before|after but not in universe
//     as a StrictUniverseMismatch violation.
//   - Implicit-unchanged: a key in universe but NOT in expected requires
//     reflect.DeepEqual between before[key] and after[key]; difference =>
//     UndeclaredChange violation.
//
// Zero external dependencies — uses reflect.DeepEqual so this file can be
// dropped into any Go 1.21+ project without third-party assertion libraries.
//
// Source of truth: Python module at `nwave_ai/state_delta/`. Keep the contract
// in sync; deviations are bugs.

package statedelta

import (
	"encoding/json"
	"fmt"
	"reflect"
	"sort"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// Snapshot models the full observable state captured at one point in time.
// Keys are port-exposed slot names (never internal struct/field names).
type Snapshot map[string]interface{}

// PredicateResult is the outcome of a predicate evaluation.
// Ok=true passes; Ok=false records a violation with an optional reason.
type PredicateResult struct {
	Ok     bool
	Reason string
}

// Pass is a convenience constructor for a successful PredicateResult.
func Pass() PredicateResult { return PredicateResult{Ok: true} }

// Fail builds a failing PredicateResult with a human-readable reason.
func Fail(reason string) PredicateResult { return PredicateResult{Ok: false, Reason: reason} }

// Predicate evaluates a (old, new) transition for a single universe slot.
// Implementations should be deterministic and side-effect free.
type Predicate struct {
	Name string
	Fn   func(oldValue, newValue interface{}) PredicateResult
}

// Eval runs the predicate, recovering from panics so a buggy predicate
// surfaces as a clean failure instead of crashing the test process.
func (p Predicate) Eval(oldValue, newValue interface{}) (result PredicateResult) {
	defer func() {
		if r := recover(); r != nil {
			result = Fail(fmt.Sprintf("predicate panicked: %v", r))
		}
	}()
	return p.Fn(oldValue, newValue)
}

// ViolationKind classifies why a universe slot failed.
type ViolationKind string

const (
	UndeclaredChange       ViolationKind = "undeclared_change"
	PredicateFailed        ViolationKind = "predicate_failed"
	StrictUniverseMismatch ViolationKind = "strict_universe_mismatch"
)

// Violation is one aggregated failure produced by AssertStateDelta.
type Violation struct {
	Kind          ViolationKind
	Key           string
	Old           interface{}
	New           interface{}
	PredicateName string // empty when the violation is not a predicate failure
	Reason        string // empty unless the predicate returned a reason
}

// String renders a single violation for diagnostics.
func (v Violation) String() string {
	var b strings.Builder
	fmt.Fprintf(&b, "  kind=%q key=%q old=%s new=%s",
		string(v.Kind), v.Key, jsonOrFallback(v.Old), jsonOrFallback(v.New))
	if v.PredicateName != "" {
		fmt.Fprintf(&b, " predicate_name=%q", v.PredicateName)
	}
	if v.Reason != "" {
		fmt.Fprintf(&b, " reason=%q", v.Reason)
	}
	return b.String()
}

// StateDeltaViolation aggregates the violations detected in a single
// AssertStateDelta call. Returned by AssertStateDeltaErr for callers that
// prefer Go-idiomatic error handling over testing.T.
type StateDeltaViolation struct {
	Violations []Violation
}

func (e *StateDeltaViolation) Error() string {
	var b strings.Builder
	fmt.Fprintf(&b, "AssertStateDelta: %d violation(s) detected:", len(e.Violations))
	for _, v := range e.Violations {
		b.WriteString("\n")
		b.WriteString(v.String())
	}
	return b.String()
}

func jsonOrFallback(v interface{}) string {
	if v == nil {
		return "null"
	}
	if b, err := json.Marshal(v); err == nil {
		return string(b)
	}
	return fmt.Sprintf("%+v", v)
}

// ---------------------------------------------------------------------------
// Predicate factories — mirror nwave_ai/state_delta/predicates.py
// ---------------------------------------------------------------------------

// Unchanged passes iff reflect.DeepEqual(old, new).
func Unchanged() Predicate {
	return Predicate{
		Name: "unchanged()",
		Fn: func(oldV, newV interface{}) PredicateResult {
			if reflect.DeepEqual(oldV, newV) {
				return Pass()
			}
			return Fail(fmt.Sprintf("expected unchanged, got old=%s new=%s",
				jsonOrFallback(oldV), jsonOrFallback(newV)))
		},
	}
}

// SetTo passes iff reflect.DeepEqual(new, value). Old is ignored.
func SetTo(value interface{}) Predicate {
	return Predicate{
		Name: fmt.Sprintf("set_to(%s)", jsonOrFallback(value)),
		Fn: func(_ interface{}, newV interface{}) PredicateResult {
			if reflect.DeepEqual(newV, value) {
				return Pass()
			}
			return Fail(fmt.Sprintf("expected %s, got %s",
				jsonOrFallback(value), jsonOrFallback(newV)))
		},
	}
}

// PrependedWith passes iff new (string) == prefix + sep + old (string).
// Default separator ":" matches the Python canonical for PATH-like composition.
func PrependedWith(prefix string, sep ...string) Predicate {
	s := ":"
	if len(sep) > 0 {
		s = sep[0]
	}
	return Predicate{
		Name: fmt.Sprintf("prepended_with(%s)", prefix),
		Fn: func(oldV, newV interface{}) PredicateResult {
			oldStr, okOld := oldV.(string)
			newStr, okNew := newV.(string)
			if !okOld || !okNew {
				return Fail("prepended_with requires string old/new")
			}
			expected := prefix + s + oldStr
			if newStr == expected {
				return Pass()
			}
			return Fail(fmt.Sprintf("expected %q, got %q", expected, newStr))
		},
	}
}

// AppendedWith passes iff new (string) == old (string) + sep + suffix.
func AppendedWith(suffix string, sep ...string) Predicate {
	s := ":"
	if len(sep) > 0 {
		s = sep[0]
	}
	return Predicate{
		Name: fmt.Sprintf("appended_with(%s)", suffix),
		Fn: func(oldV, newV interface{}) PredicateResult {
			oldStr, okOld := oldV.(string)
			newStr, okNew := newV.(string)
			if !okOld || !okNew {
				return Fail("appended_with requires string old/new")
			}
			expected := oldStr + s + suffix
			if newStr == expected {
				return Pass()
			}
			return Fail(fmt.Sprintf("expected %q, got %q", expected, newStr))
		},
	}
}

// Containing passes iff `substring` is contained in `new` — substring for
// strings, deep-equal element membership for slices.
func Containing(substring interface{}) Predicate {
	return Predicate{
		Name: fmt.Sprintf("containing(%s)", jsonOrFallback(substring)),
		Fn: func(_ interface{}, newV interface{}) PredicateResult {
			if newStr, ok := newV.(string); ok {
				if subStr, ok := substring.(string); ok {
					if strings.Contains(newStr, subStr) {
						return Pass()
					}
					return Fail(fmt.Sprintf("%q not in %q", subStr, newStr))
				}
			}
			rv := reflect.ValueOf(newV)
			if rv.Kind() == reflect.Slice || rv.Kind() == reflect.Array {
				for i := 0; i < rv.Len(); i++ {
					if reflect.DeepEqual(rv.Index(i).Interface(), substring) {
						return Pass()
					}
				}
				return Fail(fmt.Sprintf("element %s not found in slice",
					jsonOrFallback(substring)))
			}
			return Fail("containing: unsupported new value type")
		},
	}
}

// NormalizedTo passes iff normalizer(old) == normalizer(new) under DeepEqual.
// Used for transformations equivalent under a normalisation function (e.g.
// $HOME expansion, case folding).
func NormalizedTo(normalizer func(interface{}) interface{}) Predicate {
	return Predicate{
		Name: "normalized_to(<normalizer>)",
		Fn: func(oldV, newV interface{}) PredicateResult {
			if reflect.DeepEqual(normalizer(oldV), normalizer(newV)) {
				return Pass()
			}
			return Fail("normalized values differ")
		},
	}
}

// IdempotentAfter passes iff prefix is the first segment of new (split by sep).
// Used to assert a prepend-if-absent operation left the slot untouched because
// the prefix was already present.
func IdempotentAfter(prefix string, sep ...string) Predicate {
	s := ":"
	if len(sep) > 0 {
		s = sep[0]
	}
	return Predicate{
		Name: fmt.Sprintf("idempotent_after(%s)", prefix),
		Fn: func(_ interface{}, newV interface{}) PredicateResult {
			newStr, ok := newV.(string)
			if !ok {
				return Fail("idempotent_after requires string new")
			}
			parts := strings.SplitN(newStr, s, 2)
			if len(parts) > 0 && parts[0] == prefix {
				return Pass()
			}
			return Fail(fmt.Sprintf("first segment of %q is not %q", newStr, prefix))
		},
	}
}

// LegacyHealed passes iff detector(old) AND healedCheck(new) are both true.
// Mirrors the D-11 4-case paper-trace pattern for migrating fabricated legacy
// values to a healed shape.
func LegacyHealed(detector func(interface{}) bool, healedCheck func(interface{}) bool) Predicate {
	return Predicate{
		Name: "legacy_healed(<det>,<heal>)",
		Fn: func(oldV, newV interface{}) PredicateResult {
			if detector(oldV) && healedCheck(newV) {
				return Pass()
			}
			return Fail("legacy_healed: detector or healed_check failed")
		},
	}
}

// ---------------------------------------------------------------------------
// Slice-shaped helpers (Go extension — beyond Python parity)
//
// The Python predicates work on colon-separated strings (PATH-style). Go code
// more commonly holds slices as state. These helpers cover that idiom without
// modifying the Python-parity functions above.
// ---------------------------------------------------------------------------

// AppendedWithItem passes iff new is `append(old, item)` for slice state.
// Renamed from `Appended` to avoid collision with the string-shaped
// `AppendedWith` above.
func AppendedWithItem(item interface{}) Predicate {
	return Predicate{
		Name: fmt.Sprintf("appended_with_item(%s)", jsonOrFallback(item)),
		Fn: func(oldV, newV interface{}) PredicateResult {
			oldSlice, okOld := toSlice(oldV)
			newSlice, okNew := toSlice(newV)
			if !okOld || !okNew {
				return Fail("appended_with_item requires slice old/new")
			}
			if len(newSlice) != len(oldSlice)+1 {
				return Fail(fmt.Sprintf("expected len %d, got %d",
					len(oldSlice)+1, len(newSlice)))
			}
			for i := range oldSlice {
				if !reflect.DeepEqual(oldSlice[i], newSlice[i]) {
					return Fail(fmt.Sprintf("prefix divergence at index %d", i))
				}
			}
			if !reflect.DeepEqual(newSlice[len(newSlice)-1], item) {
				return Fail("tail element does not deep-equal expected item")
			}
			return Pass()
		},
	}
}

// PrependedWithItem passes iff new is `[item, old...]` for slice state.
func PrependedWithItem(item interface{}) Predicate {
	return Predicate{
		Name: fmt.Sprintf("prepended_with_item(%s)", jsonOrFallback(item)),
		Fn: func(oldV, newV interface{}) PredicateResult {
			oldSlice, okOld := toSlice(oldV)
			newSlice, okNew := toSlice(newV)
			if !okOld || !okNew {
				return Fail("prepended_with_item requires slice old/new")
			}
			if len(newSlice) != len(oldSlice)+1 {
				return Fail(fmt.Sprintf("expected len %d, got %d",
					len(oldSlice)+1, len(newSlice)))
			}
			if !reflect.DeepEqual(newSlice[0], item) {
				return Fail("head element does not deep-equal expected item")
			}
			for i := range oldSlice {
				if !reflect.DeepEqual(oldSlice[i], newSlice[i+1]) {
					return Fail(fmt.Sprintf("tail divergence at index %d", i))
				}
			}
			return Pass()
		},
	}
}

// toSlice converts a generic interface{} into a []interface{} when the
// underlying value is a slice or array. Returns ok=false otherwise.
func toSlice(v interface{}) ([]interface{}, bool) {
	if v == nil {
		return nil, false
	}
	if s, ok := v.([]interface{}); ok {
		return s, true
	}
	rv := reflect.ValueOf(v)
	if rv.Kind() != reflect.Slice && rv.Kind() != reflect.Array {
		return nil, false
	}
	out := make([]interface{}, rv.Len())
	for i := 0; i < rv.Len(); i++ {
		out[i] = rv.Index(i).Interface()
	}
	return out, true
}

// ---------------------------------------------------------------------------
// Driving functions — AssertStateDelta + AssertStateDeltaErr
// ---------------------------------------------------------------------------

// Options carry optional knobs for AssertStateDelta.
type Options struct {
	// Strict reports any key in before|after that is NOT in universe as a
	// StrictUniverseMismatch violation. Default false.
	Strict bool
}

// AssertStateDelta is the driving entry point for tests. It collects all
// violations across the universe, calls t.Errorf for each, then t.FailNow
// once so the test fails atomically with the full violation context.
//
// For each key in `universe`:
//   - If the key has a predicate in `expected`, the predicate is called with
//     `(before[key], after[key])`. A non-Ok result records a PredicateFailed.
//   - If the key is NOT in `expected`, `before[key]` must DeepEqual
//     `after[key]`. A difference records an UndeclaredChange violation
//     (implicit-unchanged enforcement).
//
// Strict mode: any key present in `before` or `after` but not in `universe`
// records a StrictUniverseMismatch violation.
func AssertStateDelta(
	t *testing.T,
	before, after Snapshot,
	universe []string,
	expected map[string]Predicate,
	opts ...Options,
) {
	t.Helper()
	err := AssertStateDeltaErr(before, after, universe, expected, opts...)
	if err == nil {
		return
	}
	violation := err.(*StateDeltaViolation)
	for _, v := range violation.Violations {
		t.Errorf("state-delta violation: %s", v.String())
	}
	t.FailNow()
}

// AssertStateDeltaErr is the testing.T-free variant for Go-idiomatic error
// handling. Returns nil on success, *StateDeltaViolation on any violation.
func AssertStateDeltaErr(
	before, after Snapshot,
	universe []string,
	expected map[string]Predicate,
	opts ...Options,
) error {
	options := Options{}
	if len(opts) > 0 {
		options = opts[0]
	}

	// Universe-deduplication (mirrors Python `set` semantics).
	universeSet := make(map[string]struct{}, len(universe))
	for _, k := range universe {
		universeSet[k] = struct{}{}
	}

	var violations []Violation

	if options.Strict {
		seen := make(map[string]struct{})
		for k := range before {
			seen[k] = struct{}{}
		}
		for k := range after {
			seen[k] = struct{}{}
		}
		var extras []string
		for k := range seen {
			if _, ok := universeSet[k]; !ok {
				extras = append(extras, k)
			}
		}
		sort.Strings(extras)
		for _, key := range extras {
			violations = append(violations, Violation{
				Kind: StrictUniverseMismatch,
				Key:  key,
				Old:  before[key],
				New:  after[key],
			})
		}
	}

	// Iterate the universe in sorted order — deterministic violation ordering
	// matters for diff-friendly test failure messages.
	keys := make([]string, 0, len(universeSet))
	for k := range universeSet {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, key := range keys {
		oldValue := before[key]
		newValue := after[key]
		predicate, hasExpected := expected[key]

		if hasExpected {
			result := predicate.Eval(oldValue, newValue)
			if !result.Ok {
				violations = append(violations, Violation{
					Kind:          PredicateFailed,
					Key:           key,
					Old:           oldValue,
					New:           newValue,
					PredicateName: predicate.Name,
					Reason:        result.Reason,
				})
			}
			continue
		}

		// Implicit-unchanged enforcement.
		if !reflect.DeepEqual(oldValue, newValue) {
			violations = append(violations, Violation{
				Kind: UndeclaredChange,
				Key:  key,
				Old:  oldValue,
				New:  newValue,
			})
		}
	}

	if len(violations) > 0 {
		return &StateDeltaViolation{Violations: violations}
	}
	return nil
}

// NWAVE-POLYGLOT-GO v1 — pilot template. Python canonical source of truth
// lives at `nwave_ai/state_delta/`. Updates to the Python contract must be
// ported here.
