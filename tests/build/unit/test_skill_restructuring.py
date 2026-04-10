"""Tests for skill restructuring to nw-prefixed SKILL.md format.

Step 01-02: Restructure 3 troubleshooter skills (pilot).
Step 02-01: Restructure all 146 non-colliding skills (bulk migration).
"""

from pathlib import Path

import pytest


SKILLS_DIR = Path(__file__).resolve().parents[3] / "nWave" / "skills"

EXPECTED_TROUBLESHOOTER_SKILLS = [
    "nw-five-whys-methodology",
    "nw-investigation-techniques",
    "nw-post-mortem-framework",
]

# Content hashes captured before restructuring (md5)
TROUBLESHOOTER_HASHES = {
    "nw-five-whys-methodology": "173de8180be48771ee151fddea3f35db",
    "nw-investigation-techniques": "b04c2a2ec34ed186c238518788ea7640",
    "nw-post-mortem-framework": "5f31098a93108aea8373715a6f7f2485",
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
    "nw-agent-creation-workflow": "9c18760734ef8702c68581e940c57df1",
    "nw-agent-testing": "58093930e354b85b07be5fe0a08fc4ed",
    "nw-ai-workflow-tutorials": "93e15d83c8b2042102785dff4c677bb7",
    "nw-architectural-styles-tradeoffs": "f6dc4a1e0f1ac40d9d1dd0d25d9c90f4",
    "nw-architecture-patterns": "1ffa321694e4b81dc268efc9d20a30b1",
    "nw-assessment-kirkpatrick": "abaecd7a3e1d040b4a4b53971e1716d8",
    "nw-authoritative-sources": "29aa67bf5e4dd89382504767654ed6a4",
    "nw-backward-design-ubd": "8e88399482057722474748531482667f",
    "nw-bdd-methodology": "09cef8098c75b9f1504a9f547c6e6bb4",
    "nw-bdd-requirements": "b7c1a43670bd2f98426c6971605b63e9",
    "nw-brainstorming": "e1b52438744b39ae52c37c89d7b4b338",
    "nw-buddy": "de628ca01961c8a99e191b789b7dd21d",
    "nw-buddy-command-catalog": "403ff4bf5cc44e73183e6021e0e3147d",
    "nw-buddy-project-reading": "239f764ac3b8b27feae1aa0c0be9bf3f",
    "nw-buddy-ssot-knowledge": "7a801cc1b1ab7379a258f621a08a71f5",
    "nw-buddy-wave-knowledge": "a6ac94dcca543dc426e22d47dffcdb28",
    "nw-cialdini-outreach": "90aea943d1a2eb313561ecbd0f2c5915",
    "nw-cicd-and-deployment": "2195ace1646b4c0ced64070d57bb542a",
    "nw-cognitive-load-management": "3e06303c46182b62288a7bffeb342909",
    "nw-cognitive-load-theory": "3f710887e887cdea6555b301b104902b",
    "nw-collaboration-and-handoffs": "88a1f50ed559281ac672f784253eb843",
    "nw-collapse-detection": "d9d627bef17d03649583302e18482570",
    "nw-command-design-patterns": "ed39642cc074ad30d53cf345a915c45d",
    "nw-command-optimization-workflow": "c9152d7ea4b3c1657ebcac9a439fcdee",
    "nw-competitive-analysis": "ec05866d4429c42ea27d84aad891f719",
    "nw-compliance-framework": "5574d1c462405437898f603dce12340e",
    "nw-copy-paste-quality": "5dfcb24d42977804b8638aa11010c5f6",
    "nw-copywriting-frameworks": "53d9774ad655abd12963cce48c90e135",
    "nw-css-implementation-recipes": "2f603190952ac6308a16f358a4fea9a3",
    "nw-curriculum-series-design": "cfc09ee152b468fe1f170a1d8afefe73",
    "nw-data-architecture-patterns": "319bf0158dcd71391e144be1abda9446",
    "nw-data-source-catalog": "2aeb92d37d80a9446692ba3b2546c4f9",
    "nw-database-technology-selection": "f0e061724fe5a77c7fcf4e9cd56f17a5",
    "nw-ddd-event-modeling": "486ed0acfe9a38624c03395ff1e268f4",
    "nw-ddd-eventsourcing": "f014437fa2b76008896d3a83e4f48288",
    "nw-ddd-strategic": "1bee905e197ac9f2cacf4e5e37f3f8ef",
    "nw-ddd-tactical": "7ec690c487144de353ae7d01ba24cd6c",
    "nw-deliver-orchestration": "554feea5efff15d9811cf44c5e682559",
    "nw-deployment-strategies": "a73beb26bce3706db567f8cce3497b9b",
    "nw-design-methodology": "9f161d6ae6ad061a6a4eb7dcb63c082c",
    "nw-design-patterns": "b0e3f59bfde50d1a7bb6ada40ca9b3b4",
    "nw-discovery-methodology": "9aaa21156acebc19a94298afe517e1a8",
    "nw-discovery-workflow": "4602c7858e3e1b8221af03c888086dc5",
    "nw-diverge": "0b577138c83c6f64501e32b3157a9a2d",
    "nw-diverger-review-criteria": "1049555d0db9de4d8b8a1e0405ca6595",
    "nw-divio-framework": "8bb88b5fb6f476838b10b61c419119ba",
    "nw-domain-driven-design": "d3afa990b8d65675d17015c41bed49e3",
    "nw-dor-validation": "8f7e905593670b0c497e9743c5d6d6e0",
    "nw-dossier-templates": "1a9c49a2f61fccff22c828260e3026b3",
    "nw-entity-resolution": "4e84222a5674af4765809ba03800696c",
    "nw-fisher-ury-preparation": "62edcbc7f0f7598821cbeca3b440e9a2",
    "nw-formal-verification-tlaplus": "0708381a1fb1aec638c3efa6ef377f78",
    "nw-fp-algebra-driven-design": "d9cdbe8eb60c311b9c74dc2033f39f9c",
    "nw-fp-clojure": "abc40c7289b4e66579ca141f14172551",
    "nw-fp-domain-modeling": "889c821f8d504cc2f452dad642b95d7b",
    "nw-fp-fsharp": "b3504a0b3a6291a14c2f3f6cf64f0cea",
    "nw-fp-haskell": "23b2853d66698175dc9943f92e38cd6e",
    "nw-fp-hexagonal-architecture": "17238db083120200562c66def3eb928c",
    "nw-fp-kotlin": "45f000b498c9f758731e08c26b261d90",
    "nw-fp-principles": "09347e33304d4bca829fa020232fe867",
    "nw-fp-scala": "f1fc1f7aa77359938a9096b55e77e408",
    "nw-fp-usable-design": "1a00bf92aa1821c4c215b4bb46f4bb31",
    "nw-futuristic-color-typography": "5c5897eed3b496ecce7b2b940e12a93e",
    "nw-gamification-mda-wow-aha": "c4e7a921d649f098534c5d238c8271f6",
    "nw-hexagonal-testing": "0de49f81beb7bbcb8654cf2f050ce604",
    "nw-icp-design": "45578e183c03c5047d1ac44c74880941",
    "nw-infrastructure-and-observability": "f190e2f9695ec7b42695c746496a9e4d",
    "nw-interaction-choreography": "8707cda3fea5be7df1daa63d6f56660f",
    "nw-interviewing-techniques": "fffd5344322d67d5070f3a7e4f435304",
    "nw-investigation-techniques": "b04c2a2ec34ed186c238518788ea7640",
    "nw-it-specific-pedagogy": "0a144003672f4a21f40fd99f69704148",
    "nw-jtbd-analysis": "325735a2314231e61af6f7f819f3baa7",
    "nw-jtbd-bdd-integration": "c0226577d42aef2f8ac314b1a4001841",
    "nw-jtbd-core": "7c211aab49cd6d81b331953ae334081a",
    "nw-jtbd-interviews": "4388705b8621dabdc147ae7f2339e839",
    "nw-jtbd-opportunity-scoring": "8ea710665dca4bfaa3b5a7be6ea7889c",
    "nw-jtbd-workflow-selection": "aee0783104e8c92406059a4b702caf62",
    "nw-lean-canvas-methodology": "48c07e56722bf48fc7ad09a67d48d1ff",
    "nw-leanux-methodology": "d32f2a9a8ba8cd15abd99f9de5c87777",
    "nw-legacy-refactoring-ddd": "ed9663407c695825a75409fed2ea51a3",
    "nw-liberating-structures-facilitation": "4d8439cf00314e03f2bb0ad53ae890a8",
    "nw-mikado-method": "baf8b356ceb4c873c0868096e3aba6d7",
    "nw-neuroscience-learning": "f9aa5c8d0acaa3821a194585025c83f5",
    "nw-online-facilitation-miro-boards": "b72b458f543eb19d2895d23b72b52f98",
    "nw-operational-safety": "d572b9c8e546cc78fb3cb6f5d4d6fb31",
    "nw-opportunity-mapping": "106bcedf09936b11730234cac7400407",
    "nw-outcome-kpi-framework": "9079b26f7000249f1deb8210039fa33d",
    "nw-pbt-dotnet": "614fcadcf7589327426fac240212e4fa",
    "nw-pbt-erlang-elixir": "85b03026cd801bb9aa88af515bc23137",
    "nw-pbt-fundamentals": "669e0d950d122d2eb0975f5c4dc7e12f",
    "nw-pbt-go": "629a6d1930c05f21da98f06225c3ebc3",
    "nw-pbt-haskell": "e28bba247b22609280214655f1b50747",
    "nw-pbt-jvm": "a6227b730ab646f9d006450c3752a788",
    "nw-pbt-python": "6b0748511bdefd79777a2f4b9c998c8d",
    "nw-pbt-rust": "59f9328e4c1b6f94d8761c8440d1f316",
    "nw-pbt-stateful": "adb77facce00fe56c7ebc642abd59a27",
    "nw-pbt-typescript": "461d6e3987c13eb66005e755db39e5a6",
    "nw-pedagogy-bloom-andragogy": "ae7f9e75d0c3e02cb07faefb4b919482",
    "nw-persona-jtbd-analysis": "6f77c93d06a99d54a0511599e55b455a",
    "nw-platform-engineering-foundations": "137a9f433ae656b4853a5d66caa896ff",
    "nw-pricing-frameworks": "3bd645624b50c048bf6e01bb7fa13aac",
    "nw-production-readiness": "d94eaa53a822fb6ca220a442cb0782f9",
    "nw-production-safety": "2a9b76c9a548a9986b06a6b6c99437c4",
    "nw-progressive-refactoring": "35e590c9df632bcfa04098d6246e5bd9",
    "nw-property-based-testing": "5f07746e743c026c59102f476e3ae77a",
    "nw-proposal-structure": "6703c77e63466b6e911b02afeddc4514",
    "nw-psychological-safety": "106382f562186d415f5b5ad1430542b7",
    "nw-quality-framework": "461e7183cc413fe7655b9fd430856e1a",
    "nw-quality-validation": "41cee9327afa9d4e579b7c0699eb544d",
    "nw-query-optimization": "17959230c1a5f619b4a172e5e8196068",
    "nw-research-methodology": "e4910ea40aefc82f421640138986f300",
    "nw-review-output-format": "459675d5bf34cb0e3385133bdba87f58",
    "nw-review-workflow": "caa53b43f091166167e49b98f40af1f8",
    "nw-roadmap-design": "4d00e7a6794a81e4ffbe4bafad5895b8",
    "nw-roadmap-review-checks": "9470251073ac44ffc154c57e53e867a5",
    "nw-sd-case-studies": "d55bf7d35ffe48db3a04425b3e8596c1",
    "nw-sd-framework": "4e5958639f9e4eb9117d581f165a7e5a",
    "nw-sd-patterns": "f7b924a26a499520b4eaaa4a0b23e20e",
    "nw-sd-patterns-advanced": "c857dfa4b586e796146ed0ee8c245285",
    "nw-sci-fi-design-patterns": "55e26b7d46745d10f0e03e726a1c7866",
    "nw-security-and-governance": "37b7d66456ce43c2817d7e0be5faaa37",
    "nw-security-by-design": "1f998c527a0d90be35648bbdd4fbc15d",
    "nw-sequence-design": "c007d97de97bfbb70803b414fd6ab6e6",
    "nw-shared-artifact-tracking": "4931f925978f1032ee398dc5998a38e3",
    "nw-signal-detection": "8cd56c60dc2d43743e88b2e8ce399685",
    "nw-source-verification": "0c9a94d055e58634c55d32fe7c6cf4a8",
    "nw-stakeholder-engagement": "32b0f2710a6afb70fa434a2a55962fac",
    "nw-stress-analysis": "ad5e1b64848a4343e749ec99c61f3517",
    "nw-taste-evaluation": "93f3f75be13aae0ec1a260ca68af94b7",
    "nw-tbr-methodology": "40e44f3c469968c140bd7c107b536644",
    "nw-tdd-methodology": "c7a8c61b0c6155198c919cbe16ae2baa",
    "nw-tdd-review-enforcement": "0bff90d97c6c449555a7415b8d829a80",
    "nw-test-design-mandates": "aa32545c69f8fc8634cc7637a813e800",
    "nw-test-organization-conventions": "64778077de4b55a493e89cf0e06ce681",
    "nw-test-refactoring-catalog": "9dd4d17224b32058386f4413027253bd",
    "nw-tlaplus-verification": "39ba15e1845e237a9d2014c467aa56ff",
    "nw-tutorial-structure": "9cb0099f21b1190abf2ed2166c6e2d8f",
    "nw-usability-engineering": "0fd991a15911cb39158396906b8ebd16",
    "nw-user-story-mapping": "104afdc456a9c7c8d05cd3910cfd2afb",
    "nw-ux-desktop-patterns": "4fc6bfc86d9c6f7ad1eaa1f9e09f48fb",
    "nw-ux-emotional-design": "fd02a828c5bf352fd438d5250f6850ee",
    "nw-ux-principles": "25c5074d1dd34e76a8a15f7c92c58772",
    "nw-ux-tui-patterns": "08a2153ea16ec80e16946e324bf3274d",
    "nw-ux-web-patterns": "34fb487a2efe03de1f8526da8f214de9",
    "nw-voss-negotiation": "a97eb0ec6357ee6d0b1c572549aead0d",
    "nw-wizard-shared-rules": "178aa443f0e4acba5b98ba4123055917",
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


class TestTroubleshooterSkillRestructuring:
    """Step 01-02: Verify troubleshooter skills are restructured."""

    @pytest.mark.parametrize("skill_name", EXPECTED_TROUBLESHOOTER_SKILLS)
    def test_skill_directory_exists_with_skill_md(self, skill_name: str) -> None:
        """Each troubleshooter skill must exist as nw-{name}/SKILL.md."""
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_file.exists(), (
            f"Expected {skill_file.relative_to(SKILLS_DIR)} to exist"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_TROUBLESHOOTER_SKILLS)
    def test_skill_content_preserved(self, skill_name: str) -> None:
        """Content must be identical to original after restructuring."""
        import hashlib

        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"{skill_name}/SKILL.md does not exist yet")

        content = skill_file.read_bytes()
        actual_hash = hashlib.md5(content).hexdigest()
        assert actual_hash == TROUBLESHOOTER_HASHES[skill_name], (
            f"Content hash mismatch for {skill_name}: "
            f"expected {TROUBLESHOOTER_HASHES[skill_name]}, got {actual_hash}"
        )

    def test_old_troubleshooter_directory_removed(self) -> None:
        """The old agent-grouped troubleshooter/ directory should not contain
        the migrated files."""
        old_dir = SKILLS_DIR / "troubleshooter"
        old_files = [
            "five-whys-methodology.md",
            "investigation-techniques.md",
            "post-mortem-framework.md",
        ]
        for filename in old_files:
            old_file = old_dir / filename
            assert not old_file.exists(), (
                f"Old file {old_file.relative_to(SKILLS_DIR)} should have been moved"
            )


class TestBulkSkillRestructuring:
    """Step 02-01: Verify all 146 non-colliding skills are restructured to
    nw-prefixed SKILL.md format."""

    @pytest.mark.parametrize("skill_name", EXPECTED_BULK_SKILLS)
    def test_skill_directory_exists_with_skill_md(self, skill_name: str) -> None:
        """Each non-colliding skill must exist as nw-{name}/SKILL.md."""
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_file.exists(), (
            f"Expected {skill_file.relative_to(SKILLS_DIR)} to exist"
        )

    def test_total_nw_prefixed_skill_count(self) -> None:
        """Total nw-* directories should be 149 (146 bulk + 3 troubleshooter)."""
        nw_dirs = sorted(
            d for d in SKILLS_DIR.iterdir() if d.is_dir() and d.name.startswith("nw-")
        )
        skill_dirs_with_md = [d for d in nw_dirs if (d / "SKILL.md").exists()]
        assert len(skill_dirs_with_md) >= 149, (
            f"Expected >= 149 nw-*/SKILL.md directories, found {len(skill_dirs_with_md)}"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_BULK_SKILLS)
    def test_skill_content_preserved(self, skill_name: str) -> None:
        """Content must be identical to original after restructuring."""
        import hashlib

        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"{skill_name}/SKILL.md does not exist yet")

        content = skill_file.read_bytes()
        actual_hash = hashlib.md5(content).hexdigest()
        assert actual_hash == BULK_HASHES[skill_name], (
            f"Content hash mismatch for {skill_name}: "
            f"expected {BULK_HASHES[skill_name]}, got {actual_hash}"
        )

    @pytest.mark.parametrize("agent_dir", FULLY_EMPTIED_AGENT_DIRS)
    def test_fully_emptied_agent_directories_removed(self, agent_dir: str) -> None:
        """Agent directories with only non-colliding skills should be removed."""
        old_dir = SKILLS_DIR / agent_dir
        assert not old_dir.exists(), (
            f"Old directory {agent_dir}/ should have been removed after migration"
        )
