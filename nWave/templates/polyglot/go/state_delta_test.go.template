// state_delta_test.go — rapid + standard testing contract tests for the Go port.
//
// Mirrors `tests/state_delta/unit/test_matcher.py` and the predicate tests for
// the Python canonical. Property-based assertions via pgregory.net/rapid where
// the universe semantic is quantified (one PBT per predicate is the
// layered-unit minimum).

package statedelta

import (
	"errors"
	"sort"
	"testing"

	"pgregory.net/rapid"
)

// ---------------------------------------------------------------------------
// Walking skeleton + core semantics
// ---------------------------------------------------------------------------

func TestAssertStateDelta_ReturnsOnCleanPrependTransition(t *testing.T) {
	AssertStateDelta(t,
		Snapshot{"PATH": "/usr/bin"},
		Snapshot{"PATH": "/des/bin:/usr/bin"},
		[]string{"PATH"},
		map[string]Predicate{"PATH": PrependedWith("/des/bin")},
	)
}

func TestAssertStateDeltaErr_ReportsPredicateFailureWithFullContext(t *testing.T) {
	err := AssertStateDeltaErr(
		Snapshot{"PATH": "/usr/bin"},
		Snapshot{"PATH": "/wrong"},
		[]string{"PATH"},
		map[string]Predicate{"PATH": PrependedWith("/des/bin")},
	)
	if err == nil {
		t.Fatal("expected violation, got nil")
	}
	var sdv *StateDeltaViolation
	if !errors.As(err, &sdv) {
		t.Fatalf("expected *StateDeltaViolation, got %T", err)
	}
	if len(sdv.Violations) != 1 {
		t.Fatalf("expected 1 violation, got %d", len(sdv.Violations))
	}
	v := sdv.Violations[0]
	if v.Kind != PredicateFailed {
		t.Errorf("kind: want %q got %q", PredicateFailed, v.Kind)
	}
	if v.Key != "PATH" {
		t.Errorf("key: want PATH got %q", v.Key)
	}
	if v.PredicateName != "prepended_with(/des/bin)" {
		t.Errorf("predicate name: want prepended_with(/des/bin) got %q", v.PredicateName)
	}
}

func TestAssertStateDeltaErr_ImplicitUnchangedCatchesUndeclaredChange(t *testing.T) {
	err := AssertStateDeltaErr(
		Snapshot{"PATH": "/u/bin", "HOME": "/home/u"},
		Snapshot{"PATH": "/des/bin:/u/bin", "HOME": "/home/changed"},
		[]string{"PATH", "HOME"},
		map[string]Predicate{"PATH": PrependedWith("/des/bin")},
	)
	if err == nil {
		t.Fatal("expected violation, got nil")
	}
	sdv := err.(*StateDeltaViolation)
	if len(sdv.Violations) != 1 {
		t.Fatalf("expected 1 violation, got %d", len(sdv.Violations))
	}
	v := sdv.Violations[0]
	if v.Kind != UndeclaredChange || v.Key != "HOME" {
		t.Errorf("expected UndeclaredChange on HOME, got %+v", v)
	}
}

func TestAssertStateDeltaErr_CollectsMultipleViolationsA7(t *testing.T) {
	err := AssertStateDeltaErr(
		Snapshot{"PATH": "/u", "HOME": "/h", "X": "1"},
		Snapshot{"PATH": "/wrong", "HOME": "/h2", "X": "1"},
		[]string{"PATH", "HOME", "X"},
		map[string]Predicate{
			"PATH": PrependedWith("/des"),
			"HOME": Unchanged(),
		},
	)
	if err == nil {
		t.Fatal("expected violations, got nil")
	}
	sdv := err.(*StateDeltaViolation)
	if len(sdv.Violations) != 2 {
		t.Fatalf("expected 2 violations, got %d", len(sdv.Violations))
	}
	keys := []string{sdv.Violations[0].Key, sdv.Violations[1].Key}
	sort.Strings(keys)
	if keys[0] != "HOME" || keys[1] != "PATH" {
		t.Errorf("expected keys [HOME PATH], got %v", keys)
	}
}

func TestAssertStateDeltaErr_StrictModeFlagsExtraKeys(t *testing.T) {
	err := AssertStateDeltaErr(
		Snapshot{"PATH": "/u", "EXTRA": "x"},
		Snapshot{"PATH": "/des:/u", "EXTRA": "x2"},
		[]string{"PATH"},
		map[string]Predicate{"PATH": PrependedWith("/des")},
		Options{Strict: true},
	)
	if err == nil {
		t.Fatal("expected violation, got nil")
	}
	sdv := err.(*StateDeltaViolation)
	found := false
	for _, v := range sdv.Violations {
		if v.Kind == StrictUniverseMismatch && v.Key == "EXTRA" {
			found = true
		}
	}
	if !found {
		t.Errorf("expected StrictUniverseMismatch for EXTRA, got %+v", sdv.Violations)
	}
}

// ---------------------------------------------------------------------------
// Predicate library — Python parity
// ---------------------------------------------------------------------------

func TestUnchanged_PassesIffDeepEqual(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		v := rapid.IntRange(-1000, 1000).Draw(t, "v")
		if !Unchanged().Eval(v, v).Ok {
			t.Fatalf("unchanged should pass for identical value %d", v)
		}
	})
	if Unchanged().Eval(1, 2).Ok {
		t.Error("unchanged should fail for 1 vs 2")
	}
	if !Unchanged().Eval(map[string]int{"a": 1}, map[string]int{"a": 1}).Ok {
		t.Error("unchanged should pass for deep-equal maps")
	}
}

func TestPrependedWith_StringComposition(t *testing.T) {
	if !PrependedWith("/des/bin").Eval("/usr/bin", "/des/bin:/usr/bin").Ok {
		t.Error("expected pass for clean prepend")
	}
	if PrependedWith("/des/bin").Eval("/usr/bin", "/wrong").Ok {
		t.Error("expected fail for wrong composition")
	}
	rapid.Check(t, func(t *rapid.T) {
		tail := rapid.String().Draw(t, "tail")
		composed := "PRE:" + tail
		if !PrependedWith("PRE").Eval(tail, composed).Ok {
			t.Fatalf("PBT: expected PRE:%q composition to pass", tail)
		}
	})
}

func TestAppendedWith_StringComposition(t *testing.T) {
	if !AppendedWith(".bak").Eval("/etc/hosts", "/etc/hosts:.bak").Ok {
		t.Error("expected pass for clean append")
	}
	if AppendedWith(".bak").Eval("/etc/hosts", "/etc/hosts").Ok {
		t.Error("expected fail for missing suffix")
	}
}

func TestSetTo_IgnoresOldMatchesNew(t *testing.T) {
	if !SetTo("active").Eval("inactive", "active").Ok {
		t.Error("set_to should ignore old")
	}
	if SetTo("active").Eval("inactive", "pending").Ok {
		t.Error("set_to should fail when new differs")
	}
	if !SetTo(map[string]int{"k": 1}).Eval(nil, map[string]int{"k": 1}).Ok {
		t.Error("set_to should deep-equal complex values")
	}
}

func TestContaining_StringAndSlice(t *testing.T) {
	if !Containing("/usr/bin").Eval("", "/des/bin:/usr/bin").Ok {
		t.Error("containing should find substring")
	}
	if Containing("/usr/bin").Eval("", "/des/bin:/opt/bin").Ok {
		t.Error("containing should fail when substring absent")
	}
	if !Containing(map[string]int{"id": 1}).Eval(nil, []interface{}{
		map[string]int{"id": 1},
		map[string]int{"id": 2},
	}).Ok {
		t.Error("containing should find deep-equal element in slice")
	}
}

func TestNormalizedTo_ComparesUnderNormaliser(t *testing.T) {
	expandHome := func(v interface{}) interface{} {
		if s, ok := v.(string); ok {
			// trivial $HOME expansion
			for i := 0; i+5 <= len(s); i++ {
				if s[i:i+5] == "$HOME" {
					return s[:i] + "/home/u" + s[i+5:]
				}
			}
		}
		return v
	}
	if !NormalizedTo(expandHome).Eval("/home/u/.local/bin", "$HOME/.local/bin").Ok {
		t.Error("normalized_to should equate $HOME-expanded paths")
	}
	if NormalizedTo(expandHome).Eval("/home/u/.local/bin", "$HOME/.other/bin").Ok {
		t.Error("normalized_to should fail when normalised values differ")
	}
}

func TestIdempotentAfter_FirstSegmentMatches(t *testing.T) {
	if !IdempotentAfter("DES_BIN").Eval("anything", "DES_BIN:/usr/bin").Ok {
		t.Error("idempotent_after should pass when prefix is first segment")
	}
	if IdempotentAfter("DES_BIN").Eval("anything", "/usr/bin:/opt/bin").Ok {
		t.Error("idempotent_after should fail when first segment differs")
	}
}

func TestLegacyHealed_FourCasePaperTrace(t *testing.T) {
	const legacy = "DES_BIN:SYSTEM_PATH_FALLBACK"
	detector := func(v interface{}) bool { s, _ := v.(string); return s == legacy }
	healed := func(v interface{}) bool {
		s, _ := v.(string)
		return s != legacy && len(s) > 8 && s[:8] == "DES_BIN:"
	}
	pred := LegacyHealed(detector, healed)
	if !pred.Eval(legacy, "DES_BIN:/usr/bin").Ok {
		t.Error("legacy_healed should pass when old is legacy and new is healed")
	}
	if pred.Eval(legacy, legacy).Ok {
		t.Error("legacy_healed should fail when new is still legacy")
	}
	if pred.Eval("/usr/bin", "DES_BIN:/usr/bin").Ok {
		t.Error("legacy_healed should fail when old was not legacy")
	}
}

func TestPrependedWithItem_SliceComposition(t *testing.T) {
	if !PrependedWithItem("a").Eval([]interface{}{}, []interface{}{"a"}).Ok {
		t.Error("expected pass for prepend to empty slice")
	}
	if !PrependedWithItem("a").Eval([]interface{}{"x"}, []interface{}{"a", "x"}).Ok {
		t.Error("expected pass for prepend")
	}
	if PrependedWithItem("a").Eval([]interface{}{"x"}, []interface{}{"x", "a"}).Ok {
		t.Error("expected fail when item is appended not prepended")
	}
	if PrependedWithItem("a").Eval([]interface{}{"x"}, []interface{}{"a"}).Ok {
		t.Error("expected fail when tail is lost")
	}
}

func TestAppendedWithItem_SliceComposition(t *testing.T) {
	if !AppendedWithItem("z").Eval([]interface{}{}, []interface{}{"z"}).Ok {
		t.Error("expected pass for append to empty slice")
	}
	if !AppendedWithItem("z").Eval([]interface{}{"x"}, []interface{}{"x", "z"}).Ok {
		t.Error("expected pass for append")
	}
	if AppendedWithItem("z").Eval([]interface{}{"x"}, []interface{}{"z", "x"}).Ok {
		t.Error("expected fail when item is prepended not appended")
	}
}

// ---------------------------------------------------------------------------
// Universe semantics — PBT
// ---------------------------------------------------------------------------

func TestUniverse_ForbidsHiddenMutationOnAdjacentSlot(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		oldHome := rapid.StringMatching(`[a-z]{1,8}`).Draw(t, "oldHome")
		newHome := rapid.StringMatching(`[a-z]{1,8}`).Draw(t, "newHome")
		if oldHome == newHome {
			t.Skip("trivial — equal values would not trigger violation")
		}
		err := AssertStateDeltaErr(
			Snapshot{"PATH": "/u", "HOME": oldHome},
			Snapshot{"PATH": "/des:/u", "HOME": newHome},
			[]string{"PATH", "HOME"},
			map[string]Predicate{"PATH": PrependedWith("/des")},
		)
		if err == nil {
			t.Fatalf("expected violation for hidden HOME mutation %q -> %q", oldHome, newHome)
		}
	})
}

func TestUniverse_PermitsMutationOnlyWithMatchingPredicate(t *testing.T) {
	err := AssertStateDeltaErr(
		Snapshot{"PATH": "/u", "HOME": "/h"},
		Snapshot{"PATH": "/des:/u", "HOME": "/h"},
		[]string{"PATH", "HOME"},
		map[string]Predicate{"PATH": PrependedWith("/des")},
	)
	if err != nil {
		t.Fatalf("expected no violation, got %v", err)
	}
}
