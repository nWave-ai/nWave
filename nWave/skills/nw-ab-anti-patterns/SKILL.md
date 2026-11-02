---
name: nw-ab-anti-patterns
description: "KNOWLEDGE — agent/skill/command anti-pattern catalog with fixes. Reference scanned by validate-spec; no sequence."
user-invocable: false
---

# nw-ab-anti-patterns (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference catalog). Scanned by `nw-ab-validate-spec` (anti-pattern step). No forced sequence.

| Anti-Pattern | Why It Fails | Fix |
|-------------|-------------|-----|
| Monolithic agent (2000+ lines) | Context rot; 3x token cost | Extract to Skills, target 200-400 lines |
| Embedded safety frameworks | Duplicates platform; wastes tokens | Construct safety first — tool surface (frontmatter `tools`/`permissionMode`), typed grammar; hooks last resort (GDP-0) |
| Aggressive language | Overtriggering on Opus 4.6 | Calm, direct statements |
| Zero examples | Fails on subtle/critical behaviors | Include 3-5 canonical examples |
| Exhaustive examples (30+) | Diminishing returns; context rot | Keep 3-5 diverse canonical cases |
| Specifying default behaviors | 65% of specs redundant | Specify only divergent behaviors |
| Negatively phrased rules | Less effective than affirmative | Phrase affirmatively |
| Compound instructions | Confuses agent reasoning | Split into separate focused steps |
| Inconsistent terminology | Amplifies confusion in longer contexts | One term per concept throughout |
| Mirrored skill loading | Frontmatter skill also loaded by a body directive or table row — the installer already preloaded it once, so the body duplicates resident knowledge | Delete the body directive/row; frontmatter alone keeps it resident |
| Handwritten conditional index | Skill Loading section or table written beside the generated region — two indexes drift | Apply the source-aware Skill addressing procedure in `nw-agent-creation-workflow`; retain one generated index and report missing source capability |
| Conditional skill in frontmatter | A skill needed only under a condition is eagerly preloaded on every task | Move it to a precise conditional trigger through the source-aware procedure; do not manufacture a registry in an installed project |
| Over-compressed examples | `### Example N:` headers removed during compression — eval tools can't find them | Keep example section headers verbatim |
| Compressed AskUserQuestion options | Runtime menu items compressed to pipes — lose decision tree structure | Preserve numbered options with descriptions verbatim |
| Broad multi-job asset | One agent/skill does N jobs; runtime re-decides "what good means" each run | Split into N one-job-one-trigger INTERNAL skills — do not add rules, do not parameterize |
| Renaming/proliferating the command surface | Renaming an established command (e.g. `forge`) or adding new user-facing commands breaks muscle-memory + the preserve-names rule | Route the split to internal skills behind the EXISTING command/agent; preserve names; a new command is the rare exception, named `/nw-*` |
