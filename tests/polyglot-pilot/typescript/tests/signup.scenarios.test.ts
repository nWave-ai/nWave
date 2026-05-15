/**
 * signup.scenarios.test.ts — generated from feature-scenarios.ts.template
 * for the polyglot pilot toy feature.
 *
 * Pillars 1+2 — domain-language scenarios composed from step methods imported
 * from signup.specifications. Vitest picks up .test.ts files automatically.
 */

import { describe, it } from "vitest";

import {
  Given_aFreshSignupRegistry,
  When_userSignsUpWithEmail,
  Then_userIsAddedToRegistryAndAuditedOnce,
  When_userAttemptsDuplicateSignup,
  Then_secondSignupIsRejectedAndStateIsUnchanged,
} from "./signup.specifications";

describe("signup — polyglot pilot", () => {
  it("User signs up with a valid email and is added to the registry", async () => {
    await Given_aFreshSignupRegistry();
    await When_userSignsUpWithEmail("alice@example.com");
    await Then_userIsAddedToRegistryAndAuditedOnce("alice@example.com");
  });

  it("Duplicate signup is rejected and leaves registry+audit unchanged", async () => {
    await Given_aFreshSignupRegistry();
    await When_userSignsUpWithEmail("alice@example.com");

    await When_userAttemptsDuplicateSignup("alice@example.com");
    await Then_secondSignupIsRejectedAndStateIsUnchanged();
  });
});
