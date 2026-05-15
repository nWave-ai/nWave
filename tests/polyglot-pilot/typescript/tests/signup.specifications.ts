/**
 * signup.specifications.ts — step-method module for the polyglot pilot.
 *
 * Generated from feature-specifications.ts.template. Differs from the
 * template in one respect: lifecycle is established by Given_ explicitly
 * (constructs a fresh app + baseline), NOT by a vitest `beforeEach`. This
 * keeps the step-method module decoupled from the test-runner's collection
 * mechanism (a `.ts` import is not a `.test.ts` file and vitest will not
 * collect lifecycle hooks from it).
 */

import { expect } from "vitest";

import {
  assertStateDelta,
  arrayAppended,
  unchanged,
  StateDeltaViolation,
} from "./common/state-delta";

import { ProductionApp } from "../src/app";

// ---------------------------------------------------------------------------
// Test fixture — established by Given_aFreshSignupRegistry().
// Module-scope is acceptable for a sequential vitest pilot; for parallel
// execution use AsyncLocalStorage or a per-scenario fixture object.
// ---------------------------------------------------------------------------

let app: ProductionApp;
let stateBefore: Record<string, unknown>;

const SIGNUP_UNIVERSE = ["registry.users", "audit.events"] as const;

// ---------------------------------------------------------------------------
// Step methods
// ---------------------------------------------------------------------------

export async function Given_aFreshSignupRegistry(): Promise<void> {
  app = new ProductionApp();
  stateBefore = await app.captureUniverse([...SIGNUP_UNIVERSE]);
}

export async function When_userSignsUpWithEmail(email: string): Promise<void> {
  await app.signup({ email });
}

export async function Then_userIsAddedToRegistryAndAuditedOnce(
  email: string,
): Promise<void> {
  const normalized = email.trim().toLowerCase();
  const stateAfter = await app.captureUniverse([...SIGNUP_UNIVERSE]);
  assertStateDelta({
    before: stateBefore,
    after: stateAfter,
    universe: [...SIGNUP_UNIVERSE],
    expected: {
      "registry.users": arrayAppended({ email: normalized }),
      "audit.events": arrayAppended({ type: "UserSignedUp", email: normalized }),
    },
  });
}

export async function When_userAttemptsDuplicateSignup(email: string): Promise<void> {
  // Re-baseline so the next Then_ measures the duplicate's delta only.
  stateBefore = await app.captureUniverse([...SIGNUP_UNIVERSE]);
  try {
    await app.signup({ email });
  } catch {
    // Expected — duplicate rejection. Then_ asserts the observable zero-delta.
  }
}

export async function Then_secondSignupIsRejectedAndStateIsUnchanged(): Promise<void> {
  const stateAfter = await app.captureUniverse([...SIGNUP_UNIVERSE]);
  try {
    assertStateDelta({
      before: stateBefore,
      after: stateAfter,
      universe: [...SIGNUP_UNIVERSE],
      expected: {
        "registry.users": unchanged(),
        "audit.events": unchanged(),
      },
    });
  } catch (err) {
    if (err instanceof StateDeltaViolation) {
      expect.fail(err.message);
    }
    throw err;
  }
}
