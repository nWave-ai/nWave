"""Tests for skill restructuring to nw-prefixed SKILL.md format.

Step 01-02: Restructure 3 troubleshooter skills (pilot).
Step 02-01: Restructure all 146 non-colliding skills (bulk migration).

Track B.1 collapse (2026-04-28): the migration is stable (last skill
content change in commit e9dd9ef7 / PR #15 merged 2026-04-28). Per the
"after migration GREEN + 1 stable release, collapse parametrize regression
nets to single-iteration tests" rule, the 315-test net is collapsed to 3
single-iteration tests. The TROUBLESHOOTER_HASHES + BULK_HASHES dicts and
EXPECTED_*_SKILLS / FULLY_EMPTIED_AGENT_DIRS lists remain as module-level
constants so failure messages still identify the broken skill by name.
"""

import hashlib
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parents[3] / "nWave" / "skills"

EXPECTED_TROUBLESHOOTER_SKILLS = [
    "nw-five-whys-methodology",
    "nw-investigation-techniques",
    "nw-post-mortem-framework",
]

# Content hashes captured before restructuring (SHA-256)
TROUBLESHOOTER_HASHES = {
    "nw-five-whys-methodology": "f5c7c63ff379aa23f0c26a9daecebcbbbc8a6952a830d1815908d011c40ee2c0",
    "nw-investigation-techniques": "e110e1f70fff941e13940ea18237c90c3fc3caf0098ccbb6cf1729bb8e4c725a",
    "nw-post-mortem-framework": "ca6a9c988ff063ef7167401b7757681251de4fff9f7bc8e92ae09df2da0a5aa3",
}

# Step 02-01: All 146 non-colliding skills to migrate (bulk)
# Excludes: critique-dimensions (7), review-criteria (7), review-dimensions (2)
EXPECTED_BULK_SKILLS = [
    "nw-agent-creation-workflow",
    "nw-agent-testing",
    "nw-ai-workflow-tutorials",
    "nw-architectural-styles-tradeoffs",
    "nw-architecture-patterns",
    "nw-assessment-kirkpatrick",
    "nw-authoritative-sources",
    "nw-backward-design-ubd",
    "nw-bdd-methodology",
    "nw-bdd-requirements",
    "nw-brainstorming",
    "nw-buddy",
    "nw-buddy-command-catalog",
    "nw-buddy-project-reading",
    "nw-buddy-ssot-knowledge",
    "nw-buddy-wave-knowledge",
    "nw-cialdini-outreach",
    "nw-cicd-and-deployment",
    "nw-cognitive-load-management",
    "nw-cognitive-load-theory",
    "nw-collaboration-and-handoffs",
    "nw-collapse-detection",
    "nw-command-design-patterns",
    "nw-command-optimization-workflow",
    "nw-competitive-analysis",
    "nw-compliance-framework",
    "nw-copy-paste-quality",
    "nw-copywriting-frameworks",
    "nw-css-implementation-recipes",
    "nw-curriculum-series-design",
    "nw-data-architecture-patterns",
    "nw-data-source-catalog",
    "nw-database-technology-selection",
    "nw-ddd-event-modeling",
    "nw-ddd-eventsourcing",
    "nw-ddd-strategic",
    "nw-ddd-tactical",
    "nw-deliver-orchestration",
    "nw-deployment-strategies",
    "nw-design-methodology",
    "nw-design-patterns",
    "nw-discovery-methodology",
    "nw-discovery-workflow",
    "nw-diverge",
    "nw-diverger-review-criteria",
    "nw-divio-framework",
    "nw-domain-driven-design",
    "nw-dor-validation",
    "nw-dossier-templates",
    "nw-entity-resolution",
    "nw-fisher-ury-preparation",
    "nw-formal-verification-tlaplus",
    "nw-fp-algebra-driven-design",
    "nw-fp-clojure",
    "nw-fp-domain-modeling",
    "nw-fp-fsharp",
    "nw-fp-haskell",
    "nw-fp-hexagonal-architecture",
    "nw-fp-kotlin",
    "nw-fp-principles",
    "nw-fp-scala",
    "nw-fp-usable-design",
    "nw-futuristic-color-typography",
    "nw-gamification-mda-wow-aha",
    "nw-hexagonal-testing",
    "nw-icp-design",
    "nw-infrastructure-and-observability",
    "nw-interaction-choreography",
    "nw-interviewing-techniques",
    "nw-investigation-techniques",
    "nw-it-specific-pedagogy",
    "nw-jtbd-analysis",
    "nw-jtbd-bdd-integration",
    "nw-jtbd-core",
    "nw-jtbd-interviews",
    "nw-jtbd-opportunity-scoring",
    "nw-jtbd-workflow-selection",
    "nw-lean-canvas-methodology",
    "nw-leanux-methodology",
    "nw-legacy-refactoring-ddd",
    "nw-liberating-structures-facilitation",
    "nw-mikado-method",
    "nw-neuroscience-learning",
    "nw-online-facilitation-miro-boards",
    "nw-operational-safety",
    "nw-opportunity-mapping",
    "nw-outcome-kpi-framework",
    "nw-pbt-dotnet",
    "nw-pbt-erlang-elixir",
    "nw-pbt-fundamentals",
    "nw-pbt-go",
    "nw-pbt-haskell",
    "nw-pbt-jvm",
    "nw-pbt-python",
    "nw-pbt-rust",
    "nw-pbt-stateful",
    "nw-pbt-typescript",
    "nw-pedagogy-bloom-andragogy",
    "nw-persona-jtbd-analysis",
    "nw-platform-engineering-foundations",
    "nw-pricing-frameworks",
    "nw-production-readiness",
    "nw-production-safety",
    "nw-progressive-refactoring",
    "nw-property-based-testing",
    "nw-proposal-structure",
    "nw-psychological-safety",
    "nw-quality-framework",
    "nw-quality-validation",
    "nw-query-optimization",
    "nw-research-methodology",
    "nw-review-output-format",
    "nw-review-workflow",
    "nw-roadmap-design",
    "nw-roadmap-review-checks",
    "nw-sd-case-studies",
    "nw-sd-framework",
    "nw-sd-patterns",
    "nw-sd-patterns-advanced",
    "nw-sci-fi-design-patterns",
    "nw-security-and-governance",
    "nw-security-by-design",
    "nw-sequence-design",
    "nw-shared-artifact-tracking",
    "nw-signal-detection",
    "nw-source-verification",
    "nw-stakeholder-engagement",
    "nw-stress-analysis",
    "nw-taste-evaluation",
    "nw-tbr-methodology",
    "nw-tdd-methodology",
    "nw-tdd-review-enforcement",
    "nw-test-design-mandates",
    "nw-test-organization-conventions",
    "nw-test-refactoring-catalog",
    "nw-tlaplus-verification",
    "nw-tutorial-structure",
    "nw-usability-engineering",
    "nw-user-story-mapping",
    "nw-ux-desktop-patterns",
    "nw-ux-emotional-design",
    "nw-ux-principles",
    "nw-ux-tui-patterns",
    "nw-ux-web-patterns",
    "nw-voss-negotiation",
    "nw-wizard-shared-rules",
]

BULK_HASHES = {
    "nw-agent-creation-workflow": "98a9ef586280a4fb486612610224f55e66d057dafbf566cba50115a568af958a",
    "nw-agent-testing": "a4a488b1f4d8ce79b481145933c398137db161bfa8c3e5fb70b20238d59bfd4c",
    "nw-ai-workflow-tutorials": "be37b1cbae22e4b0fb8e7e57b623e436da46ba78b06e1642046745225c2f1a33",
    "nw-architectural-styles-tradeoffs": "c7ea53f3af39669e5f5af0ede98194ffabea7d3daa7595605bcf7658dfb51272",
    "nw-architecture-patterns": "eed561da83212d6f51d6b9ad44a542fc54bdee14448120ebf28cdfa005c86b28",
    "nw-assessment-kirkpatrick": "eab8b30b437e12c036dd8639e34deefea5f0dd85aa3198fa684ba09045bfd384",
    "nw-authoritative-sources": "7c93e458a194355c7763ff4a60b9ee07278eb26ee41a9e0c1c721693a66c52e0",
    "nw-backward-design-ubd": "6f3d0761a098601c620fdd6dd5eb2e063b4dc0698a85f91cc4f02b6efc801e38",
    "nw-bdd-methodology": "d7b984b8b6438258c0289bd2aa12dc841f0772d451ca818bbff18c4aceea415d",
    "nw-bdd-requirements": "6091f8a557c1a3f8c94755808979a338504861e3fbb4d51ee5fe89b0c2b4f731",
    "nw-brainstorming": "688f7e9e20e813328a7dd6f6c543a7d5ca52ec45e7dd29e09815d514cff678aa",
    # Hash updated 2026-04-28: D7 mandatory Read-tool instruction landed
    # (Lean Wave Documentation epic v3.14). nw-buddy now imperatively reads
    # docs/reference/global-config.md before answering config questions.
    # Updated 2026-05-03 (v3.14.0-rc1 prep): nw-buddy gained "Version-awareness"
    # handler section directing it to read whats-new-v<MAJOR><MINOR>/ folders
    # when answering version/changelog/fix questions. See commit prep.
    # Updated 2026-05-21 (wtbd-44 uv-first migration): graceful-degradation
    # diagnostic hint now checks both `uv tool list` and `pipx list` instead
    # of pipx-only.
    "nw-buddy": "181707d7f0a0a75e839dc9f2a00c8300d9d72142e1e2d9bee1d62c5f77b4816a",
    "nw-buddy-command-catalog": "2e3a269113841286fb82dfda2619ddd419af5c92c98a3642d10a94d27bab4e4c",
    "nw-buddy-project-reading": "aacb24988ca658cf3eff3c99fec1b53fb2d6480a4ea0cea1b327398990dace7e",
    "nw-buddy-ssot-knowledge": "19293f5d5b5d12814f1a8ab0c31979c83b92a3a8bd006e57f410fa30e605ab96",
    # Hash updated 2026-05-14: TDD 3-phase canon (ADR-025) propagation —
    # DELIVER wave description now cites 3-phase RED→GREEN→COMMIT with legacy fallback.
    "nw-buddy-wave-knowledge": "f77a688312230a3fbdcdd74d89b9a70f7192de021dbc4aa381d1974ab2677c76",
    "nw-cialdini-outreach": "f3b93c4d1abefc225bc66fc0e054a76595e80b2b8bb682d6a9231f750918c22b",
    "nw-cicd-and-deployment": "5c1c98a7f6335eb182d4401a2dc6a98ad127924b1c0931fcb63d1816cbc1d3b8",
    "nw-cognitive-load-management": "692cfc4d99d5760d67a537dbff39560e8be72497ef27355c430661fc0a0420f3",
    "nw-cognitive-load-theory": "21f01f529a84cb99173dd747dc81c9609958df97c5d42648646d35a62ab9960b",
    # Hash updated 2026-06-12: claude-code-attribution-migration (057c8543) —
    # consolidated to a single Claude-trailer source in the collaboration
    # templates (removed 8 duplicate-trailer lines).
    "nw-collaboration-and-handoffs": "82002c83dc6cc0f88c99ed896783792e47931d41279a7899712baf3486215425",
    "nw-collapse-detection": "f6cc9d14d7908cbfcf97bd7937b5506e99faab9d5092a6f0e172d8583adf927b",
    "nw-command-design-patterns": "a406791ea4170a07eb621a2de9f07f39fc3856f21f1f7fa9c3ea5b9a9c7967c9",
    "nw-command-optimization-workflow": "360652060579cdacb4da56a6685447c6e094193a2d2c4d725a4d7be4a8c28752",
    "nw-competitive-analysis": "9b5dd28679b77ab02c1b87e56830fc5c13e4f377b4be8708ec7ac5d35a818707",
    "nw-compliance-framework": "460e62a5f6df925bbfe10aac41ce20bfac45986d0913f081a979cf980fe25b7e",
    "nw-copy-paste-quality": "671809cc59c8a613930dc97e28be2cd001255b1826bb3bffd8cedff85ceeee74",
    "nw-copywriting-frameworks": "6a3d73688ff19406547ba10a3f99e25c9d3baf1992e9b5a57e56268480af552b",
    "nw-css-implementation-recipes": "e8295daf45d169bf8718f12002eb38a74741b35f0ece60bba085c76c8c2abefe",
    "nw-curriculum-series-design": "7154611955a83d008b1ead5e79b3d45ee88018b5d0464958eca128a63b367392",
    "nw-data-architecture-patterns": "27fa7113dc70c67ddbe502a81a5915c4b9adb2b5e2eb470893bbb0077486d934",
    "nw-data-source-catalog": "9c71590c25cf4a7f24bdf96770367bcdde1fcf0d5c9b0c59ea87d57ad037f0dd",
    "nw-database-technology-selection": "9c05a1dc0f39eeb79f3000c1a1b8b35ae40530c1bdc569cabacd75d96478d1be",
    "nw-ddd-event-modeling": "c028a1b806c3043760957a61888624ea23c7731f0aba33a3d68c468cb8be95f9",
    "nw-ddd-eventsourcing": "def99ce43e0432befcc7ee704b7e9a18bcdb794f615eec9adb919ed066964f94",
    "nw-ddd-strategic": "b6ee12524feabbca6097efd3e6b48893c0c0b7500fb7038db13c3b6e95ef0360",
    "nw-ddd-tactical": "7eb1a4b35848d10006f431a118ba21ced9b77d7023f3f725a1a723d141eec338",
    "nw-deliver-orchestration": "18c771bcc9cbfbdd5b14c37a56a4ec5a0da9ea0fd01a1217ad4b5f8838f53a98",
    "nw-deployment-strategies": "6e8c4105c4741eb8c860462326a8b94e9cf0407bd3461ba6b20e1d31608dba1d",
    "nw-design-methodology": "8ebecd812e33fce64811376008090d2f1f7e8fd6234588d36d264711daa52022",
    "nw-design-patterns": "b7bfb731708da9c485b5b3516495af45e8310db2a032b58186bddcca8320f22b",
    "nw-discovery-methodology": "9fbc2a5174c63be28bbafdf2b807fe585fd04486c0cddbb91689736af5aa4cb7",
    "nw-discovery-workflow": "8b851baf6d0c0b5873c86a568832008da4dcf9e33db31a464ea2baa717609407",
    "nw-diverge": "70b9da265d91eac027311bee366b69ca91b8b73610d22237585183ea5bbfa5ca",
    "nw-diverger-review-criteria": "f7ee3f02af05b22570e9bda34e39e432293aa79eb27ef8727e7bd4a940514eac",
    "nw-divio-framework": "38e1443f22f846ce45693a5691aa7ae5fb250fe97806a2f4b2fd71b3a98ce04e",
    "nw-domain-driven-design": "fa805ca067d53f6f1acb8e09d5afa0706b4b0b74b2e73802da8147151d35e3ae",
    "nw-dor-validation": "9378bddc4ad278717053a273ca96d1da4b29b1b2fd5dc83e74a77e3f96a0d9d8",
    "nw-dossier-templates": "08804dac68c169fbea6330573ff6d7fe7d37eb75feb62715f1ced30522b169ae",
    "nw-entity-resolution": "2026e71e787eeeca8d8f0eb72e1d1c6ab177661cb2e969a984a9a5463e817b46",
    "nw-fisher-ury-preparation": "3ab02dbd3cb3778b599bf0364564d0250e2c8bdd42a7e7b886fdfa733561c7bf",
    "nw-formal-verification-tlaplus": "25471c3404940428a937f77a4c8c6bbf8e33258bd681156e0ece89cd1833f3d2",
    "nw-fp-algebra-driven-design": "3668d869f0260250728e99c5ff2e83e8cbb5cc6f61240a79cb05811f69b3e70a",
    "nw-fp-clojure": "2bfc7a6d240d9ed68510b75756ebd144783cf7a1097e08f22e5c53030a381aa7",
    "nw-fp-domain-modeling": "10f78944b4f9034486a5be98521308fe6839f6034e171f43777394e6f474ae3b",
    "nw-fp-fsharp": "d964e86d4a6539cffd0080cfcdfd365049c4bb2a0da32cbb2eb7bfeb3f9cd332",
    "nw-fp-haskell": "55db0147b1ef9e64fcbe656341312ffd290ecadafee2b8b9af130c3ac21c444f",
    "nw-fp-hexagonal-architecture": "24c9a41e88eedc50edfc96db54a4b74682724cf8b321d2d763795b7a39838873",
    "nw-fp-kotlin": "8163e1f1ad1831f9e6e37d809c6e685f09621cdd8cb22137bd2e7ed23c40175e",
    "nw-fp-principles": "f590e3bfa75b58214590c65515e7efc0e499e3214512898997e5b0948cc729a7",
    "nw-fp-scala": "8a4f8137a561e91836ed855d92c6e169753f15f3fc0b4f9e993433f6c281276e",
    "nw-fp-usable-design": "4b3aba348ff8f348adf3054e26de848be94396203f19b7df70d022e78868ced6",
    "nw-futuristic-color-typography": "15705c6293708279d295f364f707de1789f1244f81b8b02022f2eddd6225ab7e",
    "nw-gamification-mda-wow-aha": "f556368452725c27d71161cde53b5de488ccafd862f95a93c3f3733d45f5098c",
    "nw-hexagonal-testing": "826322f613033cad6d9389df8bf983f97931df7747fc23efe3cb1d4d6050f450",
    "nw-icp-design": "f22b2171fe51dcd5bec91824f1c809ed515d9cd4d1841b6fe4d5ce0d4d2d45f8",
    "nw-infrastructure-and-observability": "d9ee8d1a5f66c1902bffd04b1c5e33bdc542f120f28288a9e35d02bb25fdcff6",
    "nw-interaction-choreography": "dceeb52b2b35c5369b5fea7ae94b230c8afd775d34161a0b30b57422665e77e4",
    "nw-interviewing-techniques": "4b0e4c1cbfda5f3cd6eb83cb3f7610b7637f24360cef967ab454a47f6f413123",
    "nw-investigation-techniques": "e110e1f70fff941e13940ea18237c90c3fc3caf0098ccbb6cf1729bb8e4c725a",
    "nw-it-specific-pedagogy": "683a288060f670391f0cfe57c9dcb82980839b0b6a44d474be07fe0c8e49224b",
    "nw-jtbd-analysis": "9b9c8c12299783e59c3a47aad021ca48750d1f3056da876b604c1d5f64470cf7",
    "nw-jtbd-bdd-integration": "465609255610bb2e88b19e28560bfcb77b3d62138be44dcfae28e9129f89d5c1",
    "nw-jtbd-core": "2ba49cb0a45d1df52db5b0571812a4e15a749cb2841076e0b2df834256339095",
    "nw-jtbd-interviews": "2888141ada8e3dd996908c2ea419e5a78dccabc6b90f0e010f5abf57e2d7542e",
    "nw-jtbd-opportunity-scoring": "26c943e8901428009bb677af9069e0644eb052a0c57567314860425ff194795a",
    "nw-jtbd-workflow-selection": "8d3bc56f988713b72204344d41eac9b0e402206eed0d51af2270f80e06cc3d57",
    "nw-lean-canvas-methodology": "0e77920997227311088f3bfaed63f7068fd174796e615776bc18205539f3eb1c",
    "nw-leanux-methodology": "1ad4f2bb74a2c73f85bd36fafda939e210e0d3021247020164bd3bcbc593e8e6",
    "nw-legacy-refactoring-ddd": "67c0b290c43da1cfad97a39fff01031b99d9dab4814c2f9e9776e4ebe3f5f774",
    "nw-liberating-structures-facilitation": "8cf8cd6ab3db91e644f5f951b7fc40c620f423f459b0826656caab4d2a843f96",
    "nw-mikado-method": "474589da3d259f15834804e719fa560bb4cf213a3ba04450e7c94c011e6061a9",
    "nw-neuroscience-learning": "712660b4567f17f96215d196d613c73b2b8e3a10ff108505398411e8a924aeaf",
    "nw-online-facilitation-miro-boards": "40c02f6c8d40b56e4ac554172ad1006c41951c96682a7e8e3e9677a90c9bde82",
    "nw-operational-safety": "2ea929228f1b65ef54f3dd16baf4bd03a08f3b09fbbc9e24d7fc0e63132f551b",
    "nw-opportunity-mapping": "a143185ccd6dd33940d6e85fcfe93ba275c247a9786a6a131b963955a295a868",
    "nw-outcome-kpi-framework": "9e9bf77b0af58d50a18e9a6bba331e177837def041fbec80d794f2b25c42e34e",
    "nw-pbt-dotnet": "a554f992c764189ad0fedf3b5e92709d0feca081271f0da369782cfea13c4880",
    "nw-pbt-erlang-elixir": "8e34c9d2b7e1af053f2b7d7399a2326507e690cfc87eb444dba76dad8e0f8e71",
    "nw-pbt-fundamentals": "e23303d9c26dc0a0609431abf47454beb73149a8c6abab77b0d88c17fbf956c5",
    "nw-pbt-go": "0f743771692bcc6c0bd5580c29e74b1d82891768634d522ab0d5b92599fe2657",
    "nw-pbt-haskell": "b62a6f5b949fc2f4db733dae6d222cfea12f33293e8ef05b31b397826b03e030",
    "nw-pbt-jvm": "6dd65d7bdf62d1fb709be10306b4146958558cbec7b70fb86c52ad09b7e8cba0",
    "nw-pbt-python": "bd1e6a65e203b811899d7944fb27b600080ad5e5c1edfa800207e44230557398",
    "nw-pbt-rust": "ab7a496a843de8d1c017e82c17a85f102c277cbaba65b093fcbde55c1626b987",
    "nw-pbt-stateful": "b02f2e58d9ecfa19be7df2d3bebb2789d57b01da82608ba99dde539d16ac9920",
    "nw-pbt-typescript": "a804bde15ba46887204c2c1722cd9323a0bd28995878a8fa1446c29b78d043c2",
    "nw-pedagogy-bloom-andragogy": "a28ec029451ae7a4face474403ecf165d93806a3c6e3991ee3a4604dc8e52c65",
    "nw-persona-jtbd-analysis": "0bfd73c58c4ae0b370b8d9340a9463308a1335b10640b9715cd56f2414d28f1d",
    "nw-platform-engineering-foundations": "6fb02ea4c3f7229a059c63bac32ab7a33338ba1e9f75e5c39b2de040f7036921",
    "nw-pricing-frameworks": "a05dce9a3238d93539062ed178049a158ccf0da44d5b0d78953da9ea24f6db5b",
    "nw-production-readiness": "e0ed73d019d81de5c1c2ba502aa22ae03fefc2c02179f2def9d57cec409f1c04",
    "nw-production-safety": "03b793065f3e128779ee753af98036ed015b2563faafb396c923599ebf80789e",
    "nw-progressive-refactoring": "c98a3e4d54409e1c0f07c6fa003d5e178b17c631d7d681acaa01bd026bce953f",
    # Updated 2026-05-19: extended "When PBT Adds Value" with closed-world
    # falsifier-gate anti-pattern + empirical anchor (commit c2637f6c8). See
    # backlog F-TEST-SPEEDUP-PARADIGM-CATALOG for context.
    "nw-property-based-testing": "f83ab800c7bf9753841f0119fb23c062bed6d37a44354d1c334637503541836f",
    "nw-proposal-structure": "85493f0b530c48f0dbe7fa078c180329b7c9f5ccb60adbf756a04cee6820504d",
    "nw-psychological-safety": "320d5ada7e5b172a888301c124c14965b9b0c487f92d2c7dd20c83acd12a4fea",
    "nw-quality-framework": "a2225528f8de2436c1e661bf93f8a6cd2fb7c2ade24c79a0b40d86c6f1eeaccf",
    "nw-quality-validation": "59fb8a28ea83eba775e7e5e5b614bec45d2ab746b86ba4d9d92dbf0cb07df9b7",
    "nw-query-optimization": "6738e287f7dbd0eb40ccb7ec5a076025a3a9c295b715dd6a0e1fb3386218a31a",
    "nw-research-methodology": "c72463c0904ccce1aff19bb142d8b31f2ea1551504c5ef09d4f3f1fab54d94c0",
    "nw-review-output-format": "81ceeb5b241e014cc8c8876f9c19d481590904c0d39d7ba4804cce541c76b626",
    "nw-review-workflow": "d02a9be6fa337cac3bb954a155ba8cdefcc3b2b7aa1a85a7515fb8876aef19d3",
    # Hash updated 2026-05-15: F-1 (fix-roadmap-json-drift, step 01-01) —
    # examples aligned to roadmap-schema.json vocabulary (name | criteria |
    # files_to_modify) to resolve schema-vs-implementation drift.
    "nw-roadmap-design": "43a95401e8cf872ca114ad1e34260ae714ae23842d697b88220c41978f1c2bac",
    "nw-roadmap-review-checks": "c1e7f662d60cc7ec29768e8d8202b2dedef29a8710226aa12f844e488b18893d",
    "nw-sd-case-studies": "fe998efd26c5916aec0a23057750f7c026e2acf07d31db9d581e144f317a7126",
    "nw-sd-framework": "2bad0995eb0e8e175abbb85c3016f07361ce8f4f3ff64fe3c944b8b7c3f1c78d",
    "nw-sd-patterns": "5f38b31c8a49d5e46fc166c0a16ac9b029c5ca0da2f70a1577c462ee029ccfc8",
    "nw-sd-patterns-advanced": "316693272d8655db6ca27e4bf18ea706a03ae1423f46f401a603c6a0dc29d4e8",
    "nw-sci-fi-design-patterns": "2ca4cc03091e39471fa008c0c324b4bccd57b9d070a6ceafefebba4cec7b0a5b",
    "nw-security-and-governance": "f14bdaaec185bca9cf11b9ed60a8ce71412429e4239b03d876d93e5b4d63e23b",
    "nw-security-by-design": "62bb8bf1da2e1240a964447a89724067a57b2d884be4f827af416e507b328808",
    "nw-sequence-design": "a4b1389389635e7f1ab34271b9d3f4c5dc7c4cf297bf9dc1e9a6bf5db37edea9",
    "nw-shared-artifact-tracking": "b8d3e734d25a6e1f9e6829b7250351d8c436492eeff1de6d6abf0eef27d0e438",
    "nw-signal-detection": "3eb7923d9005e398e34d174b1cec03653c1a12a667993cada80c866cd44aa10b",
    "nw-source-verification": "7af6655e3f3a812dcb2d2d239a2aab3cb6dd7b7b41144f41a41965843223c0b4",
    "nw-stakeholder-engagement": "bb25100247f87ef9e7b38f298e660b5b73277c97e9e40693f4b1299572346f89",
    "nw-stress-analysis": "2b56e6f9d82535b6f38d5c5a40cca7293aece63dcb66c1b1521f85bb5d768027",
    "nw-taste-evaluation": "c8bdfd3ee5a50369d6ae350400c0dcfaa3a5e2e5869903a7f3c15581125152df",
    "nw-tbr-methodology": "bf23bb275945dd01b73dc670d45f9e62ef3807de5a5799cae602cc9174d6c170",
    "nw-tdd-methodology": "3a1dc0eaf81c3ddb236eb4e206a4c34054d094b134e069e988f2c201b50a4a89",
    # Hash updated 2026-06-23: COMMIT phase routed through des-commit (#51)
    # Hash updated 2026-05-26: LANGUAGE CONVENTION FRAME banner added
    # (prevent Python-leak in non-Python projects per user-reported friction).
    # Prior hash updated 2026-05-20: ATDD-pure slice-10 — AT-completion ledger
    # + mode-scoped execution-log prose for the roadmap-free spine.
    # Prior hash updated 2026-05-15: closed-source refs scrubbed (3ab776967).
    # Prior hash updated 2026-05-14: TDD 3-phase canon (ADR-025) propagation.
    "nw-tdd-review-enforcement": "e57a44235e1a5503bdc283b33fcc576ffe01df3b1d70c209548e315d946fae07",
    "nw-test-design-mandates": "bb4758584463a5643e6c01f7e1eb4da1760b55518fe3657d06627c416c78cf1b",
    "nw-test-organization-conventions": "3da109abbab27d75aa7ed687dc0e5ad20726b5e36b84e8c248042b99fb1c22a1",
    "nw-test-refactoring-catalog": "af11cad1d79d652c115aeb21fabb08f5c3559abb9f06f067856cc79cbd14bc24",
    "nw-tlaplus-verification": "b229f4b45f70674b069f4e13e3aa6464a1c66e3ace89fabce7ec8a7db767eab2",
    "nw-tutorial-structure": "813e7f84f8aa59866246460700ea546b3b30e42a55710b4eb3d66db7bdc4fbce",
    "nw-usability-engineering": "17711123c0e01510af7d9edde4222b62be4f665ccc0790ddeabfa66f94e3902a",
    "nw-user-story-mapping": "f5e7fd97b1df45fc5c5bb69010a3dd22617e35d9f4e8f4b632ed7bd1f5037dd3",
    "nw-ux-desktop-patterns": "b63ce354f5c3bde77b3ad799906036cebaa46e96709bc4b79c096f065643d48c",
    "nw-ux-emotional-design": "e3b34cf402320b45d762ecbbdf301365ed401568b74b00f9d6900c7f9c96e5be",
    "nw-ux-principles": "feb8d25506c463a51ce2aed572e626c26c4bc2ad0163f4b538b451724e86d81a",
    "nw-ux-tui-patterns": "861735a3ab93ad1482ddc5256bb4c35a28d11d9650237cb41c62161b628c27c9",
    "nw-ux-web-patterns": "cd3334fc00ac12ba25373c8f90594b975c5d2782d381ac43f7a9031020657178",
    "nw-voss-negotiation": "712df0eae889916c7ca30b8113a4a5a69fb9f9f019b2a56d2781e3a29d610c13",
    "nw-wizard-shared-rules": "6df481ffb6b8f94f09f6f133d2c48805c046822a72627019b1962ad29fe616aa",
}


# Agent directories that should be fully emptied after migration
# (all their skills are non-colliding and will be moved)
FULLY_EMPTIED_AGENT_DIRS = [
    "business-discoverer",
    "business-osint",
    "common",
    "data-engineer",
    "deal-closer",
    "documentarist",
    "functional-software-crafter",
    "outreach-writer",
    "platform-architect",
    "product-discoverer",
    "researcher",
    "software-crafter-reviewer",
    "tutorialist",
    "ux-designer",
    "workshopper",
]

# Floor for total nw-* skill directories with SKILL.md. Migration baseline
# is 149 (146 bulk + 3 troubleshooter); subsequent waves have added more.
EXPECTED_NW_SKILL_FLOOR = 149


def test_all_nw_skills_present() -> None:
    """Every migrated skill must exist as ``nw-{name}/SKILL.md`` and the
    total count must meet the migration floor.

    Failure message lists missing skills by name so the regression is
    diagnosable without re-running 162 parametrized cases.
    """
    expected = sorted(set(EXPECTED_TROUBLESHOOTER_SKILLS) | set(EXPECTED_BULK_SKILLS))
    missing = [
        name for name in expected if not (SKILLS_DIR / name / "SKILL.md").exists()
    ]
    assert not missing, (
        "Skill directories missing nw-{name}/SKILL.md after migration: " + str(missing)
    )

    nw_dirs_with_md = [
        d
        for d in SKILLS_DIR.iterdir()
        if d.is_dir() and d.name.startswith("nw-") and (d / "SKILL.md").exists()
    ]
    assert len(nw_dirs_with_md) >= EXPECTED_NW_SKILL_FLOOR, (
        f"Expected >= {EXPECTED_NW_SKILL_FLOOR} nw-*/SKILL.md directories, "
        f"found {len(nw_dirs_with_md)}"
    )


def test_skill_content_hashes_match_baseline() -> None:
    """Every migrated skill's content hash must match the captured baseline.

    Iterates the merged hash dict (troubleshooter + bulk = 149 entries).
    Failure message identifies which skills drifted, with expected vs actual
    hashes side by side, so a single failure is as diagnosable as the
    pre-collapse 149-parametrize-case version.
    """
    baseline = {**TROUBLESHOOTER_HASHES, **BULK_HASHES}
    drifted: list[str] = []
    for skill_name, expected_hash in baseline.items():
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_file.exists():
            drifted.append(f"{skill_name}: SKILL.md missing")
            continue
        actual_hash = hashlib.sha256(skill_file.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            drifted.append(f"{skill_name}: expected {expected_hash}, got {actual_hash}")
    assert not drifted, (
        "Skill content hashes drifted from migration baseline:\n  "
        + "\n  ".join(drifted)
    )


def test_emptied_agent_dirs_are_empty() -> None:
    """Every fully-emptied agent directory must be removed after migration.

    Iterates FULLY_EMPTIED_AGENT_DIRS once; failure message lists every
    directory that still exists, so the regression is diagnosable in one
    failure rather than per-directory parametrize cases.
    """
    leftover = [
        agent_dir
        for agent_dir in FULLY_EMPTIED_AGENT_DIRS
        if (SKILLS_DIR / agent_dir).exists()
    ]
    assert not leftover, (
        "Old agent-grouped skill directories still exist after migration "
        f"(should have been removed): {leftover}"
    )
