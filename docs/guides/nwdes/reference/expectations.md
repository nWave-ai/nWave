# expectations

The examiner records with the `nwdes expectations` CLI verbs and closes. See [role recording](index.md#role-recording).

| Action | Result | Specific refusal |
|---|---|---|
| `expectations close` | Fix or replace the expectation set | UncoveredPromise if a promise has no expectation |
| `expectations close --revise` | Replace a fixed set | UncoveredPromise if a promise has no expectation |

Every public promise must be cited. The expectations prompt automatically includes the current fixed public rows in order, with their assigned IDs, complete text and promise mappings, or `None.` before first fixation. It includes no private implementation evidence.

For a revision, seed a draft from the current record with `expectations open --from-current`. Preserve unchanged rows, complete texts and promise mappings. Remove rows deliberately; add new rows without invented IDs. Cover every current public promise. Close with `--revise`.

Each expectations row cites the promises it judges with repeatable `--promise P<n>`. A row without one refuses at `expectations row add` with MissingFact naming `expectations.row.promises`.

The examiner receives the complete generated bundle inline. It works from the user's point of view and needs public product facts. It records typed values with the CLI. The root does not submit role output. Return refusals to the examiner so it can correct its values. See [Fix a bug](../fix-bug.md).

The lean route fixes expectations once after root product facts and design, before the first oracle. A Request that states its outcome needs no product-owner turn or Quint model as a product prerequisite.

Common refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, RoleNotAccepted, DanglingReference.

## Replacement dependencies

Expectation rows cite product P IDs, not design L/B/C/Y IDs. Product replacement, or `slice set` retiring a slice-owned promise, withdraws each whole row citing a retired P ID. Design replacement alone preserves these rows. Unaffected rows retain their IDs, content, and relative order.

Withdrawal of a row also withdraws exactly its E-keyed examination verdict. The cascading notice names the original expectation row in WHY, for example `expectations.rows[1] (E2) was withdrawn.` If all rows disappear, the existing expectation-set container remains with zero rows. Repair uses `expectations close --revise`.

A revision retires omitted E IDs and withdraws only their verdicts. The root can give a fresh expectations prompt to the examiner against the current product, then choose examination. No role is invoked automatically; surviving IDs alone do not prove semantic freshness.

