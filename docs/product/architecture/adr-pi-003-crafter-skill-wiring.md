# ADR-PI-003: Crafter exposed as a pi skill via resources_discover, reusing nWave skill assets

## Status
Accepted (2026-06-23). Implements D1 (crafter as `/skill:software-crafter`
contributed via `resources_discover`) at the DESIGN level.

## Context
D1 locked the crafter as a pi **skill** named `software-crafter`, contributed via
the pi extension's `resources_discover` event (idiomatic pi; maps 1:1 to nWave's
existing skill assets). nWave already ships crafter skill content under
`nWave/skills`, and the OpenCode skills plugin (`opencode_skills_plugin.py`)
demonstrates transforming those assets into a non-Claude harness's skill layout
(per-skill dir + `SKILL.md`, frontmatter rewrite, manifest, public-only filter).

## Decision
- The crafter skill **content is REUSED** from `nWave/skills` assets — no new
  authored skill. The skill states the 3-phase TDD contract (RED→GREEN→COMMIT)
  it will enforce (DoD step 2 / Story 1).
- Contribution is via the pi extension's **`resources_discover`** event returning
  the skill path(s) (`skillPaths`) — the extension is the single integration
  point, consistent with D1 and keeping the wiring inside the one TS artifact.
- Skill **file placement** is handled by the installer. **Decision: a dedicated
  `pi_skills_plugin.py` is NOT created for this thin slice.** Instead the existing
  pi DES plugin places the single crafter skill alongside the extension, because
  scope is crafter-only (D7) and a full skills-transform plugin (à la OpenCode's
  multi-skill enumerate/filter/rewrite) is unjustified for one skill. If/when pi
  scope expands beyond the crafter, promote to a `pi_skills_plugin.py` mirroring
  `opencode_skills_plugin.py` (CREATE NEW deferred, evidence-gated).

## Alternatives Considered
- **Create `pi_skills_plugin.py` now** (full mirror of OpenCode skills plugin) —
  rejected for this slice: it brings duplicate-name resolution, public-agent
  filtering, and multi-skill enumeration that a single crafter skill does not
  need. Resume-driven-development risk; defer until ≥2 skills are in pi scope.
- **Bundle the skill text inside the extension TS** — rejected: couples skill
  content to the translator, breaks reuse of the canonical `nWave/skills` asset,
  and drifts from the Claude Code crafter source of truth.
- **Expose the crafter as a pi agent** (mirroring `opencode_agents_plugin.py`) —
  rejected by D1 (skill, not agent) and D7 (no agent/orchestration in pi).

## Consequences
- Positive: single canonical crafter definition reused across harnesses; minimal
  new install surface for the thin slice.
- Positive: the extension is the only pi integration point (skill discovery +
  enforcement), simplifying the manifest and uninstall.
- Negative: the DES plugin gains a skill-placement responsibility; bounded and
  documented; flagged for promotion to a dedicated plugin when scope grows.
- Open (dependency): the exact `resources_discover` return shape (`skillPaths`
  field name) and pi's skill-directory expectation are an explicit dependency of
  this ADR — confirmed against pi 0.79.9 docs during DELIVER; flagged with R1 in
  the brief. The skill-placement path the DES plugin writes to depends on this
  resolution.
