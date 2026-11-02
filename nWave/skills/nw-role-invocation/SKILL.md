---
name: nw-role-invocation
description: "KNOWLEDGE — how a wave entrypoint invokes its specialist: the real installed role definition, never a generic persona. Load when a wave delegates to a role."
user-invocable: false
disable-model-invocation: true
---

# nw-role-invocation (KNOWLEDGE)

Reference for wave entrypoints. The LLM chooses waves and operations; nwdes constructs handoffs, briefs, prompts and packets without workflow state or progression.

## Rule

Delegate to the exact installed role definition (`nw-<role>`), with its real instructions and mandatory frontmatter skills. Missing mandatory instructions stop delegation; never substitute a generic persona. Conditional skills load on the role's own triggers. The LLM/native host owns model execution, provider/model/effort selection and orchestration. nwdes never launches a model.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly`, including its dispatch-task instruction for every relevant role.

## Invocation forms

For native delegation, select the installed specialist in the host tool:
Claude `Agent(subagent_type="nw-solution-architect", prompt=...)`;
Codex `spawn_agent(agent_type="nw-solution-architect", message=...)`.
Substitute the exact role below, and pass the bounded task and its evidence.
Do not select a generic agent and replace its definition with persona prose.
The host's native tool may be named `Agent` or `Task`; use whichever it
supports to select the exact installed role, with only parameters it supports.
The wave caller invokes the role; the role does the semantic work and records
its values through its nwdes verbs. If native delegation cannot start it with its
declared tools ceiling, use a supported native CLI invocation or report the
missing capability. Never substitute a generic worker or grant extra tools.

Read `nw-nwdes` for the current role/task mapping. Build the exact role's
task with `nwdes prompt` and pass its output verbatim. Put bounded host
context in `--root-context` only for recipes that admit it; examine refuses it
and both host observation flags before any read or effect.

| Need | Exact installed role | Role-owned recording |
|---|---|---|
| Product decomposition | `nw-product-owner` | `nwdes product` record edits, `nwdes product close` |
| Expectation charter | `nw-product-owner --task charter` | `nwdes charter set`, `charter positive add`, `charter close` |
| Solution architecture | `nw-solution-architect` | `nwdes design` record edits, `nwdes design close` |
| Acceptance oracle | `nw-acceptance-designer` | `nwdes acceptance row add`, `close`; host observes declared RED |
| Implementation | `nw-software-crafter` / `nw-functional-software-crafter` | `nwdes craft file add`, `command add`, `close`; host observes declared GREEN |
| Independent review | `nw-software-crafter-reviewer` / `nw-acceptance-designer-reviewer` | Follow [Review evidence](#review-evidence) in the generated subject/slice scope |
| Expectations / EXAMINE | `nw-user-examiner` | `nwdes expectations row add/close` or `nwdes examine verdict set/close` |
| Operational facts | `nw-platform-architect` | Give semantic operational facts to the solution architect, who records the design values |

The bound functional paradigm selects `nw-functional-software-crafter`;
otherwise use the ordinary crafter. Do not infer a new paradigm from the
launcher or host language.

### Selected independent operational review

When the authorized DESIGN or DEVOPS task selects independent platform review, the native wave caller invokes `nw-platform-architect-reviewer` on the actual current operational authority, its bound facts, authorized scope and available observations. Use the existing native invocation form and the reviewer's declared ceiling; no producer judgment substitutes for its result.

This is caller-owned orchestration, not a new review-task payload or builder operation. Add no delegation/reviewer/result fields to the design payload. Consume the actual verdict and findings; required revisions or unresolved load-bearing evidence remain with the platform authority owner. A configured or human-authorized skip is skipped, never approved. Builder success does not establish review approval or authorize rollout.

Reuse adequate authority without a new producer turn; do not add a review for a no-op when none is selected. Missing exact-role invocation capability is explicit, never a generic substitute or invented result.

## Role-owned recording

`nwdes prompt` includes the generated verb reference for
the selected role. Every recording invocation names its kind and scope.
The role records semantic values with typed `add`/`set`/`remove` flags; the first
such call creates the scoped draft. It then calls `close --outcome ... --diagnostic ...`.
nwdes constructs ids, structure, paths and serialization. The host passes
no envelope and copies no reply into another command.
The prompt binds repository, feature and applicable slice scope. Use the
generated reference for required selectors; keep the same scope throughout
the draft. Slash-separated verb lists describe separate calls, not one command.
Run every nwdes command from the top level of the checkout. Roots default to
cwd and the repository root; lane verbs resolve the main worktree. Close with
no draft validates empty values.

Every role, including the Product Owner and examiner, records through the nwdes
CLI using Bash. They work from the user's point of view and have no need to
inspect code; this is a task focus, not a code-access prohibition.
The host supplies the generated prompt, not a substitute recording channel.

For an authority correction, the owning role uses `open --from-current`, edits the
retained records and closes again. A close refusal retains the draft and leaves
authority unchanged. Give the refusal's WHAT/WHY/HOW unchanged to that role,
or fulfill its named host-owned prerequisite and rebuild the prompt if inputs
changed. The host does not repair serialization or write the role's record.

For craft, record files with `file add --path L --change
Created|Modified|Deleted` and commands with `command add --command C --exit N`.
Craft closes with `--outcome accepted|rejected --diagnostic T [--blocked-by L]`.
nwdes writes these closed records under the feature's
`runs/<kind>[.<slice>].json`, beside the handoff rather than inside it.
Their accepted outcomes replace neither host-observed GREEN nor EXAMINE.

## Review evidence

The final reviewer owns selection and sufficiency of the touched-file selected tests.
It reuses a complete applicable native result (host, CI or the normal commit hook)
whose source, test, argv and runtime inputs are unchanged, citing its original operator
and run; it executes only missing or affected checks, once. Reuse never waives a check.
Each run it actually executes is recorded with `nwdes review observation add` before it closes the review.
Selection is mechanical, never memory-picked. Each literal run text includes
actual argv, exit status, stdout and stderr, including empty or incomplete
selection and absent tooling. Large UTF-8 payloads use `--text-file PATH`;
inline payloads use `--text TEXT`. nwdes issues R ids and stamps commit/clean
itself; revise or remove by `--id R<n>` or `--at N`.

```sh
nwdes review observation add --feature search --subject candidate --text-file run.txt
nwdes review finding add --feature search --subject candidate --location L --obligation T --observation T --remediation T --owner implementation
nwdes review close --feature search --subject candidate --outcome rejected --diagnostic T
```

Keep the generated subject and slice scope. Close requires at least one
observation stamped clean at the current commit; `ReviewUnobserved` or
`StaleObservation` retains the draft for correction. Preserve actual provenance
and results. Missing observations remain indeterminate, never producer confidence.
On rejection, nwdes names every finding owner role and its read command;
the owner reads exactly its own findings with `nwdes review findings --owner O`.
Native messaging is harness-dependent. Where the host supports it, a reviewer sends each completed finding directly to its owner, naming the owner's `nwdes review findings --owner O` read; where it does not, the host route delivers that read and no message is pretended. Each completed finding goes directly to its owner. Host owns models and checker execution.
Preserve candidate source/oracle bytes and artifact ownership.


## Native execution

A batch candidate owner is an exact installed crafter (`nw-software-crafter` or `nw-functional-software-crafter` by the bound paradigm) invoked through the native form above with its execution tools. It is not a new role row and takes the batch's composition and verification duties from `nw-throughput` (Batch candidate owner); reviewers stay separate.

The host runs each slice's declared verification command itself and observes RED on the original source before craft and GREEN after craft; nwdes does not run it.
For a bugfix, never select HEAD as
the baseline after it already contains the fix. A setup, import or collection
failure is not the promised behavioral RED.

For an applicable prefactoring move, preserve the existing GREEN oracle and
support/runtime identities. Run its declared command before the move and after
only the preserving movement, before new behavior. Keep distinct production
identities and actual run evidence as `nw-code-craftsmanship` requires.

Formal checker/model runs retain receipt files beside the model, with checker
and version, literal argv, exit status, stdout/stderr and model sha256.
Cite receipt paths in the design's `evidence`; nwdes stores paths, not proof.

## Scope and permitted evidence

Resolve the explicit repository, feature handoff, slice and configured paths
once and pass them to affected roles. Include the original Request, human
exclusions/amendments and provenance in ordinary producer/reviewer context.
Do not ask the human to repeat known facts or treat producer scope reduction
as authorization.

A role with limited tools receives immutable facts and real host-run results
through its generated prompt; it records only through its declared capability.
A path is not evidence for a role that cannot read it. Truncated diff prose
is not complete review evidence.
EXAMINE judges the public contract and observed user results. Producer
classifications and source inspection do not substitute for those observations.
Reference `nw-typesafe-system-one` for role-owned unchanged-request relay;
a skill mention is not evidence of client/caller-exchange capability.

## Reviewer and examiner boundaries

For DISTILL before-code alignment, MUST read
`~/.claude/skills/nw-at-completeness-check/SKILL.md`. When the original value,
selected contract, and prior adequate alignment are unchanged with no new
finding, reuse it without another ATD review. The examiner's independent
expectations are fixed once per feature by `nwdes expectations close`, before
the first slice's acceptance designer, and revised only with
`nwdes expectations open --from-current`, then `nwdes expectations close --revise`.
Supply the fixed public expectations to the
acceptance reviewer within its evidence boundary; keep oracle authoring
independent. Alignment concerns observation feasibility and ambiguity, not
runtime acceptance.

Build the examiner's generated prompt without host observations or root context.
It names a public-only workspace, its committed public document index and
`nwdes examine read` and `nwdes examine probe`. The examiner gathers its own
public observations there and records each through its generated examination
recording verbs before citing it. `nwdes packet --kind examine` follows the same
contract; no source, diff, producer verification or private design reaches it.

Examine refuses host observation carriers. Missing public observations remain
indeterminate, never supplied from producer confidence.

Invoke the exact installed `nw-user-examiner` with its declared plain Bash
capability for public read/probe and nwdes recording. nwdes does not confine
the examiner process. Keep reviewer and examiner assessments independent;
neither inherits the producer's verdict.

The examiner's verdicts come once per feature after the final slice.
It records every current expectation with `nwdes examine verdict set`, then
calls `nwdes examine close`. The host's provider/model/session
metadata describes the actual invocation, not a nested tool or inferred run.
Neither a successful close nor a stored verdict chooses integration.


## Currentness and candidate lifecycle

Read current state before choosing the next host action. Reuse unchanged adequate
semantic authority/alignment selectively by value and consumed prerequisites;
native remeasurement is not automatic reauthoring or transitive role replay.
Source identity alone is insufficient when contract/oracle/runtime changed.
Distinguish missing facts, graph drift, owned/upstream bytes drift and destination
drift and route their concrete causes to the owner. A step's Success does not
close the authorized Request; continue until real obligations and integration
are current, stopping for a genuine human checkpoint/choice, not a recoverable
mechanical fact.

Agree commit/staging/install lifecycle before craft. Commit only owned
source/test/support/authority. Preserve foreign bytes and staging, retain actual
before/after revisions and candidate observations before removing disposable
workspaces. Edits after verification need current verification/review evidence,
not a restamped old approval. Preserve destination compare-and-swap conditions;
there is no reset recipe or automatic cleanup of user WIP.
Probes use invocation-local disposable scope or declared nonowned output, retain
their receipt and remove only their own files. Preflight actual native processes,
ports, writable build/temp/cache and separate space/inode requirements; provider
auth/quota/timeout, machine/setup failure and product rejection stay distinct.

Reuse native execution evidence only when source, oracle/supports, argv/cwd,
environment/toolchain/substrate, consumed contracts and purpose remain identical
and the assurance permits it. Independent review and stress have distinct
purposes; neither is a producer cache. Require authentic native attribution of
assertion versus setup/build/import failure where observable, otherwise
INDETERMINATE. Missing counts/reporters or unknown code-fact radius never become
zero. Accounting uses actual timeline overlap, root/child session dedup and
returned provider/Jev usage; interrupted or missing cost is unknown, not zero.

## Waiting

For native model subagents, use host completion notifications or their actual
completion handle. For a long-running native CLI/process, retain and resume its
real process handle until terminal output arrives. Never use fixed sleeps,
silence, or an invented notification as evidence of completion; never launch a
duplicate invocation while the first remains active.

## Human interaction

Offer interaction per `nw-human-collaboration`; honor an already chosen mode.
