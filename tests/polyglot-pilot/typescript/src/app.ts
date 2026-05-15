/**
 * Toy ProductionApp — minimal signup feature for the polyglot pilot.
 *
 * Composition root: constructs the in-memory registry and audit log, exposes
 * `signup` (driving operation) and `captureUniverse` (state inspection at
 * port-exposed slots). Real-feature shape: in-process domain + driven ports
 * (here both in-memory).
 *
 * Universe slots exposed:
 *   - "registry.users" : ReadonlyArray<UserRecord>
 *   - "audit.events"   : ReadonlyArray<AuditEvent>
 *
 * Internal field names are NOT part of the universe — refactoring internals
 * stays GREEN.
 */

export interface UserRecord {
  readonly email: string;
}

export interface AuditEvent {
  readonly type: string;
  readonly email: string;
}

export class DuplicateSignupError extends Error {
  constructor(public readonly email: string) {
    super(`Duplicate signup rejected: ${email}`);
    this.name = "DuplicateSignupError";
    Object.setPrototypeOf(this, DuplicateSignupError.prototype);
  }
}

export interface ProductionAppOptions {
  // Reserved for future port-swap hooks (clock, RNG, paid APIs).
  // The toy feature uses none.
}

export class ProductionApp {
  // Driven-port state (in-memory).
  private readonly users: UserRecord[] = [];
  private readonly events: AuditEvent[] = [];

  constructor(_options: ProductionAppOptions = {}) {
    // Toy feature — nothing to wire.
  }

  /**
   * Driving port — signup a user by email. Rejects duplicates by throwing
   * `DuplicateSignupError`. On success: appends to registry AND appends a
   * single `UserSignedUp` audit event.
   */
  async signup(input: { email: string }): Promise<UserRecord> {
    const email = input.email.trim().toLowerCase();
    if (email.length === 0) {
      throw new Error("signup: email must be non-empty");
    }
    if (this.users.some((u) => u.email === email)) {
      throw new DuplicateSignupError(email);
    }
    const record: UserRecord = { email };
    this.users.push(record);
    this.events.push({ type: "UserSignedUp", email });
    return record;
  }

  /**
   * State-inspection port — return a snapshot of the universe slots requested.
   * Snapshot returns deep-frozen copies so test assertions cannot mutate
   * production state by accident.
   */
  async captureUniverse(keys: readonly string[]): Promise<Record<string, unknown>> {
    const snapshot: Record<string, unknown> = {};
    for (const key of keys) {
      switch (key) {
        case "registry.users":
          snapshot[key] = this.users.map((u) => ({ ...u }));
          break;
        case "audit.events":
          snapshot[key] = this.events.map((e) => ({ ...e }));
          break;
        default:
          // Unknown slot — return undefined so state-delta sees the absence
          // explicitly rather than silently fabricating a value.
          snapshot[key] = undefined;
      }
    }
    return snapshot;
  }
}
