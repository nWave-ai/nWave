---
name: nw-requester-words
description: Use when naming DIVERGE options, writing recommendation or requester-facing text, or reviewing either — the requester-words quote match, new-term definition, `[new]` marking and handle rule
user-invocable: false
disable-model-invocation: true
---

# Requester Words

The one rule for the requester's words in a DIVERGE wave. Authoring skills and the review criteria point here.

Source: the host-written `docs/feature/{id}/diverge/request.md`. Only a `requester-verbatim` block holds the requester's words; a `host-summary` block never does. The source label is host-attested.

## Rules

1. **Quote match**: a user-words quote is a contiguous span of one `requester-verbatim` block, compared case-insensitively with whitespace collapsed; no words dropped mid-span.
2. **User-words name**: the option name (its heading handle) is the quoted span itself, after the same folding. A name that differs from its quote is coined; mark it coined.
3. **New term**: the longest noun phrase naming an option, mechanism or concept that is not a rule 1 span of any `requester-verbatim` block. A phrase only in `host-summary` blocks is new; a phrase in both kinds of block is not new. Plain quantities, durations and ordinary words are not terms. Delimiting the longest noun phrase is a judgment, not a mechanical test: extend it over modifiers that name a distinct mechanism, and when unsure mark it.
4. **Marking**: append `[new]` to a new term at its first mention in each of: the recommendation.md body, its decision statement, the DIVERGE-RESULT block, and every summary written for the requester. A term first used in the decision statement is marked there once; one used in the body and in the decision statement is marked in both.
5. **Handle**: a coined handle appears only as an options-raw.md heading and in the taste-evaluation.md scoring table. A user-words handle is the requester's own phrase, so elsewhere the same words are ordinary mechanism wording and are allowed; never cite any handle as a label ("Option N", "the X option") and never argue a score from its wording.
6. **Attribution**: write "your X" only when X is a rule 1 span.

**PASS**: block "a monthly 45-minute interactive talk"; heading `Monthly 45-minute interactive talk` with `user-words ("Monthly 45-minute  interactive talk")`; decision, the only mention of the inbox: "Proceed with the monthly 45-minute interactive talk plus a question inbox [new] for about 90 days".
**FAIL**:
- heading `Automated agent store` with `user-words ("monthly interactive talk")`: the quote matches, the name is not the quote (rule 2).
- `user-words ("monthly interactive talk")` drops "45-minute" mid-span (rule 1).
- "your agent-queryable store" attributes a host-summary-only phrase to the requester (rule 6).
- a decision statement using "question inbox" without `[new]` when the phrase is only in `host-summary` blocks or in none (rule 4); not a failure if a `requester-verbatim` block also holds it.
