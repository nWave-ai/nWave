/**
 * state-delta.test.ts — vitest contract tests for the TypeScript port.
 *
 * Mirrors `tests/state_delta/unit/test_matcher.py` and the predicate tests
 * for the Python canonical. Property-based assertions via fast-check where the
 * universe semantic is quantified (one PBT per predicate is the layered-unit
 * minimum).
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";

import {
  assertStateDelta,
  StateDeltaViolation,
  unchanged,
  prependedWith,
  appendedWith,
  setTo,
  containing,
  normalizedTo,
  idempotentAfter,
  legacyHealed,
  arrayPrepended,
  arrayAppended,
} from "./state-delta";

describe("assertStateDelta — walking skeleton + core semantics", () => {
  it("returns void on a clean prepend transition", () => {
    expect(() =>
      assertStateDelta({
        before: { PATH: "/usr/bin" },
        after: { PATH: "/des/bin:/usr/bin" },
        universe: ["PATH"],
        expected: { PATH: prependedWith("/des/bin") },
      }),
    ).not.toThrow();
  });

  it("throws StateDeltaViolation with full context on a predicate failure", () => {
    let caught: unknown = null;
    try {
      assertStateDelta({
        before: { PATH: "/usr/bin" },
        after: { PATH: "/wrong" },
        universe: ["PATH"],
        expected: { PATH: prependedWith("/des/bin") },
      });
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(StateDeltaViolation);
    const err = caught as StateDeltaViolation;
    expect(err.violations).toHaveLength(1);
    expect(err.violations[0]).toMatchObject({
      kind: "predicate_failed",
      key: "PATH",
      old: "/usr/bin",
      next: "/wrong",
      predicateName: "prepended_with(/des/bin)",
    });
    expect(err.message).toContain("PATH");
    expect(err.message).toContain("predicate_name='prepended_with(/des/bin)'");
  });

  it("implicit-unchanged catches an undeclared change", () => {
    let caught: unknown = null;
    try {
      assertStateDelta({
        before: { PATH: "/u/bin", HOME: "/home/u" },
        after: { PATH: "/des/bin:/u/bin", HOME: "/home/changed" },
        universe: ["PATH", "HOME"],
        expected: { PATH: prependedWith("/des/bin") },
      });
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(StateDeltaViolation);
    const err = caught as StateDeltaViolation;
    expect(err.violations).toHaveLength(1);
    expect(err.violations[0]).toMatchObject({
      kind: "undeclared_change",
      key: "HOME",
      old: "/home/u",
      next: "/home/changed",
    });
  });

  it("collects multiple violations into a single StateDeltaViolation (A7)", () => {
    let caught: unknown = null;
    try {
      assertStateDelta({
        before: { PATH: "/u", HOME: "/h", X: "1" },
        after: { PATH: "/wrong", HOME: "/h2", X: "1" },
        universe: ["PATH", "HOME", "X"],
        expected: { PATH: prependedWith("/des"), HOME: unchanged() },
      });
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(StateDeltaViolation);
    const err = caught as StateDeltaViolation;
    expect(err.violations).toHaveLength(2);
    const keys = err.violations.map((v) => v.key).sort();
    expect(keys).toEqual(["HOME", "PATH"]);
  });

  it("strict mode flags keys present in before|after but missing from universe", () => {
    let caught: unknown = null;
    try {
      assertStateDelta({
        before: { PATH: "/u", EXTRA: "x" },
        after: { PATH: "/des:/u", EXTRA: "x2" },
        universe: ["PATH"],
        expected: { PATH: prependedWith("/des") },
        strict: true,
      });
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(StateDeltaViolation);
    const err = caught as StateDeltaViolation;
    expect(err.violations.some((v) => v.kind === "strict_universe_mismatch" && v.key === "EXTRA")).toBe(true);
  });
});

describe("predicate library — Python parity", () => {
  it("unchanged() passes iff old deep-equals next", () => {
    fc.assert(
      fc.property(fc.anything(), (v) => {
        expect(unchanged()(v, v)).toBe(true);
      }),
    );
    expect(unchanged()(1, 2)).toBe(false);
    expect(unchanged()({ a: 1 }, { a: 1 })).toBe(true);
    expect(unchanged()({ a: 1 }, { a: 2 })).toBe(false);
  });

  it("prependedWith(prefix, sep) passes iff next === prefix + sep + old (string)", () => {
    expect(prependedWith("/des/bin")("/usr/bin", "/des/bin:/usr/bin")).toBe(true);
    expect(prependedWith("/des/bin")("/usr/bin", "/wrong")).toBe(false);
    // PBT: any tail string produces a matching composition
    fc.assert(
      fc.property(fc.string(), (tail) => {
        expect(prependedWith("PRE")(tail, `PRE:${tail}`)).toBe(true);
      }),
    );
  });

  it("appendedWith(suffix, sep) passes iff next === old + sep + suffix", () => {
    expect(appendedWith(".bak")("/etc/hosts", "/etc/hosts:.bak")).toBe(true);
    expect(appendedWith(".bak")("/etc/hosts", "/etc/hosts")).toBe(false);
  });

  it("setTo(value) ignores old and matches next", () => {
    expect(setTo("active")("inactive", "active")).toBe(true);
    expect(setTo("active")("anything", "active")).toBe(true);
    expect(setTo("active")("inactive", "pending")).toBe(false);
    expect(setTo({ k: 1 })(null, { k: 1 })).toBe(true);
  });

  it("containing(sub) checks substring (string) or array element", () => {
    expect(containing("/usr/bin")("", "/des/bin:/usr/bin")).toBe(true);
    expect(containing("/usr/bin")("", "/des/bin:/opt/bin")).toBe(false);
    expect(containing({ id: 1 })(null, [{ id: 1 }, { id: 2 }])).toBe(true);
    expect(containing({ id: 9 })(null, [{ id: 1 }, { id: 2 }])).toBe(false);
  });

  it("normalizedTo(fn) compares under a normaliser", () => {
    const expandHome = (v: unknown) =>
      typeof v === "string" ? v.replace("$HOME", "/home/u") : v;
    expect(normalizedTo(expandHome)("/home/u/.local/bin", "$HOME/.local/bin")).toBe(true);
    expect(normalizedTo(expandHome)("/home/u/.local/bin", "$HOME/.other/bin")).toBe(false);
  });

  it("idempotentAfter(prefix) checks first segment of next", () => {
    expect(idempotentAfter("DES_BIN")("anything", "DES_BIN:/usr/bin")).toBe(true);
    expect(idempotentAfter("DES_BIN")("anything", "/usr/bin:/opt/bin")).toBe(false);
  });

  it("legacyHealed(det, heal) implements the 4-case paper-trace", () => {
    const LEGACY = "DES_BIN:SYSTEM_PATH_FALLBACK";
    const pred = legacyHealed(
      (s) => s === LEGACY,
      (s) => typeof s === "string" && s !== LEGACY && s.startsWith("DES_BIN:"),
    );
    expect(pred(LEGACY, "DES_BIN:/usr/bin")).toBe(true);
    expect(pred(LEGACY, LEGACY)).toBe(false);
    expect(pred("/usr/bin", "DES_BIN:/usr/bin")).toBe(false);
  });

  it("arrayPrepended(item) matches next === [item, ...old]", () => {
    expect(arrayPrepended("a")([], ["a"])).toBe(true);
    expect(arrayPrepended("a")(["x"], ["a", "x"])).toBe(true);
    expect(arrayPrepended("a")(["x"], ["x", "a"])).toBe(false);
    expect(arrayPrepended("a")(["x"], ["a"])).toBe(false);
  });

  it("arrayAppended(item) matches next === [...old, item]", () => {
    expect(arrayAppended("z")([], ["z"])).toBe(true);
    expect(arrayAppended("z")(["x"], ["x", "z"])).toBe(true);
    expect(arrayAppended("z")(["x"], ["z", "x"])).toBe(false);
  });
});

describe("universe semantics — PBT", () => {
  it("forbids hidden mutation on adjacent slot (implicit-unchanged)", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.string({ minLength: 1 }),
        (oldHome, newHome) => {
          fc.pre(oldHome !== newHome);
          let threw = false;
          try {
            assertStateDelta({
              before: { PATH: "/u", HOME: oldHome },
              after: { PATH: "/des:/u", HOME: newHome },
              universe: ["PATH", "HOME"],
              expected: { PATH: prependedWith("/des") },
            });
          } catch {
            threw = true;
          }
          expect(threw).toBe(true);
        },
      ),
    );
  });

  it("permits mutation only on slots with matching predicates", () => {
    expect(() =>
      assertStateDelta({
        before: { PATH: "/u", HOME: "/h" },
        after: { PATH: "/des:/u", HOME: "/h" },
        universe: ["PATH", "HOME"],
        expected: { PATH: prependedWith("/des") },
      }),
    ).not.toThrow();
  });
});
