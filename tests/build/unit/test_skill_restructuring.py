"""Tests for skill restructuring to nw-prefixed SKILL.md format.

Step 01-02: Restructure 3 troubleshooter skills (pilot).
Step 02-01: Restructure all 127 non-colliding skills (bulk migration).
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
    "nw-five-whys-methodology": "85365d366270f87ea2816b1c28a633de",
    "nw-investigation-techniques": "3c0ead4dd17b84919cae872059820475",
    "nw-post-mortem-framework": "4f6fbc3a2c92da5eb536f49b83262f9e",
}

# Step 02-01: All 127 non-colliding skills to migrate (bulk)
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
    "nw-deliver-orchestration",
    "nw-deployment-strategies",
    "nw-design-methodology",
    "nw-design-patterns",
    "nw-discovery-methodology",
    "nw-discovery-workflow",
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
    "nw-it-specific-pedagogy",
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
    "nw-sci-fi-design-patterns",
    "nw-security-and-governance",
    "nw-security-by-design",
    "nw-sequence-design",
    "nw-shared-artifact-tracking",
    "nw-signal-detection",
    "nw-source-verification",
    "nw-stakeholder-engagement",
    "nw-stress-analysis",
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
    "nw-ab-critique-dimensions": "16ca2604f00bed2780adf599504d367d",
    "nw-abr-critique-dimensions": "70cb9460b1cb8ee89bab13719ad8111d",
    "nw-ad-critique-dimensions": "9e41d87da2958d36bccec9f7e6fc79ab",
    "nw-agent-creation-workflow": "53cfd98e1d0bb2fee27acfd1ac6a81b7",
    "nw-agent-testing": "9afbfb930f71bf035eb2336a89e8a2ff",
    "nw-ai-workflow-tutorials": "e6006a2c63bc81fcd229a5ec5d69ee7c",
    "nw-architectural-styles-tradeoffs": "85ea2eb234c9c6d49fc29869452aecb2",
    "nw-architecture-patterns": "70e7489935a2b37e4d0feffd031325e3",
    "nw-assessment-kirkpatrick": "fdce53dffe807e02a721f1625c270da1",
    "nw-authoritative-sources": "673a721dd36ddf97f278c2998ea587ad",
    "nw-backward-design-ubd": "40fe0eae69d872b5466577c7ae44cffb",
    "nw-bdd-methodology": "e5b083db9cb1a65c523eecd2c8296841",
    "nw-bdd-requirements": "e300ca99112acff759d0f617150351b1",
    "nw-br-review-criteria": "ba532cb8b1da6a9f8a7abe07f5e5adc5",
    "nw-canary": "552e7cd0147ad044da98cf021b34e8f8",
    "nw-cialdini-outreach": "5207947388523eca7249f60959e88ef7",
    "nw-cicd-and-deployment": "133c4dd6a1da1be8e83f8195d0f8bfaa",
    "nw-cognitive-load-management": "95c9cd2054de9afad5db18119e8eb7f0",
    "nw-cognitive-load-theory": "434824ba8f5f110cc4f7ea512b452755",
    "nw-collaboration-and-handoffs": "b651bfa391334917eea42ca6872f5873",
    "nw-collapse-detection": "bc3bfcc2cae8cfa7b957c4b13a62c619",
    "nw-command-design-patterns": "ec36e00d4707027918ab565cad3b6c3a",
    "nw-command-optimization-workflow": "2365ebf0c1d6504a3a2831b992e678a3",
    "nw-competitive-analysis": "00bd6be0a54102d0acf681852a22ca49",
    "nw-compliance-framework": "b79f6fd147f3bb075cb47afa1f82b8e7",
    "nw-copy-paste-quality": "d072bcdf1cc6beb6e8b0d2f50762b738",
    "nw-copywriting-frameworks": "203b966553a37355a02995ed9b5af503",
    "nw-css-implementation-recipes": "1dbb59520657040d7c29dcb17c313ef3",
    "nw-curriculum-series-design": "e2bdb31c10ed247bf2b08a3cab6e8875",
    "nw-data-architecture-patterns": "496a1bd0159a80628eb548426651f6d0",
    "nw-data-source-catalog": "7233c6ff88603e35f1f7c0701a886c96",
    "nw-database-technology-selection": "e0daa78b9b44d3e8e62f8e38182ab331",
    "nw-deliver-orchestration": "702a483d5e27a74d084fd3a4b138d2b4",
    "nw-deployment-strategies": "1d36b0661f01da6b6a8f8d53c148be76",
    "nw-der-review-criteria": "0542cd541524916f28605552339b9ee2",
    "nw-design-methodology": "705dd3301569d6cedfc0eb052d741f41",
    "nw-design-patterns": "b824970021e56729f763a7144d588e41",
    "nw-discovery-methodology": "08735ee6ba19bdb2c57fccce5ce05a80",
    "nw-discovery-workflow": "e891a7e82861a2b7c7426fd8682623e9",
    "nw-divio-framework": "00cb79e382bd5a9f23adff6a25d09a17",
    "nw-domain-driven-design": "864cd012569a0cb347cbd67cc7bdc5ed",
    "nw-dor-validation": "e04cb8d37dadb85fb4f79550ed976cae",
    "nw-dossier-templates": "72bfb6af4b00b1f51da399de9dde97f7",
    "nw-dr-review-criteria": "5baa85efe0f691f8cc14604fae35020f",
    "nw-entity-resolution": "8fad889d96826ffbca2e940114e68050",
    "nw-fisher-ury-preparation": "c8c6dc8a3d90d71bae7ae89ffa050cb6",
    "nw-five-whys-methodology": "85365d366270f87ea2816b1c28a633de",
    "nw-formal-verification-tlaplus": "b470f30887fb1551998b3be169ebb688",
    "nw-fp-algebra-driven-design": "db6bec2330239acc48a2df45ba41105e",
    "nw-fp-clojure": "d2dffee1fc562b8af50885fb96bf7b63",
    "nw-fp-domain-modeling": "578aa9032579d93e33b0d33ade6609b6",
    "nw-fp-fsharp": "ca59fb5abaec6ec21573bed3df01f181",
    "nw-fp-haskell": "2e5bcc180ed88c80da074b172f4cf1bb",
    "nw-fp-hexagonal-architecture": "8953614410c387786fa0716ffd157214",
    "nw-fp-kotlin": "1a1923d2ccd7172a172b942b12a712d6",
    "nw-fp-principles": "d1c335cdcc799412a93a47d82664b14b",
    "nw-fp-scala": "5288e1258803f17c3dc590052b2e978d",
    "nw-fp-usable-design": "0f520a8667fbc3e5340ba0cb4321a711",
    "nw-futuristic-color-typography": "6be4723f9204f8af825c8d39aa2ee10d",
    "nw-gamification-mda-wow-aha": "83aa154c13e14dba5c4b49cd81db00bf",
    "nw-hexagonal-testing": "b3f132651592fd9a92ab412bcf68e993",
    "nw-icp-design": "c4e0c66979d887148985c60d7b2e4355",
    "nw-infrastructure-and-observability": "e9bd6af0f22673f7f11a7530d7ba847d",
    "nw-interaction-choreography": "4432aefff5b495b7bd272846fd12f943",
    "nw-interviewing-techniques": "fa2f5405fe40e29d32f02724d1cffb81",
    "nw-investigation-techniques": "3c0ead4dd17b84919cae872059820475",
    "nw-it-specific-pedagogy": "022f0df6c1a5fd4416e34557142c0352",
    "nw-jtbd-bdd-integration": "281d4a04a756bb376d1c554a6e97bea1",
    "nw-jtbd-core": "72c092a932873a9516ef7674d591e769",
    "nw-jtbd-interviews": "fc1a38847843f722d6bf807a41022ede",
    "nw-jtbd-opportunity-scoring": "8596f4c3348e95c24963421eb46b887f",
    "nw-jtbd-workflow-selection": "ff7f9bfd97b2abd47cd40a9d21b96684",
    "nw-lean-canvas-methodology": "69ed03816ad43738ae1125dd10553a39",
    "nw-leanux-methodology": "58676a92ffae6ec1ee9057001892fa45",
    "nw-legacy-refactoring-ddd": "4507a66d0062189b4f9485913858c792",
    "nw-liberating-structures-facilitation": "319c11cf8f73769dc385bf148ec8aa1e",
    "nw-mikado-method": "d2ccb66664a93d42dd3d3123740a59ac",
    "nw-neuroscience-learning": "050a39f1fda9056cf9e7dc2309299623",
    "nw-online-facilitation-miro-boards": "0b33564afea32d3160a235a2603d1cd5",
    "nw-operational-safety": "e2a86b1c9931c4cae2d19944a3dc9a18",
    "nw-opportunity-mapping": "3de89022b05f62f63d60029b561eed30",
    "nw-outcome-kpi-framework": "2cc38b2e215520f00fd8cc65b15ed118",
    "nw-par-critique-dimensions": "46d541480a407ee69d28f704b0abbc45",
    "nw-par-review-criteria": "78208b87217ee62d0ba612547885aab5",
    "nw-pbt-dotnet": "a2f02d9ff2798df81489b7cfdb2a15cd",
    "nw-pbt-erlang-elixir": "587e2626a7bb516cc8c85568ceaa65aa",
    "nw-pbt-fundamentals": "d96767e2a8d8c0856256026a7ff6ff1d",
    "nw-pbt-go": "0b0e252af12abd9e3d7a6c9a2367d729",
    "nw-pbt-haskell": "f776a6d5dc7649115b03d872c67722ed",
    "nw-pbt-jvm": "5fbb7644ff210524379abe601644ff60",
    "nw-pbt-python": "5091190c6f1f1887bda50c6f8e809cc0",
    "nw-pbt-rust": "b6bdf9c7245025328d8925965578ffa8",
    "nw-pbt-stateful": "512f4a6c8574f500721d9d56251ba5f4",
    "nw-pbt-typescript": "12c43550b17ff01bea83d9d7f40ce1be",
    "nw-pdr-review-criteria": "d03a696d6995cfdb85288e0232186f42",
    "nw-pedagogy-bloom-andragogy": "af2cc9c692e4a298df927ab0bcf2f77f",
    "nw-persona-jtbd-analysis": "466dfd4448247f22f6c9fb92e8efba84",
    "nw-platform-engineering-foundations": "65c29919b06c8c7ba8e96e362dee72f8",
    "nw-po-review-dimensions": "c49c39776f46390fa57cd98929c472bb",
    "nw-por-review-criteria": "0e361de024752de21e85b533e37fded5",
    "nw-post-mortem-framework": "4f6fbc3a2c92da5eb536f49b83262f9e",
    "nw-pricing-frameworks": "a186a218eeb18ca837a75abcb1edddf5",
    "nw-production-readiness": "71a10ce33b0e6b5465a4cef4f1dbd0fb",
    "nw-production-safety": "4c515a8cf0d1424862976b65d04c275d",
    "nw-progressive-refactoring": "8f180b5c499d7b0f7516f1a3fc14ca99",
    "nw-property-based-testing": "bfa2ead3c800a08f2ef8ccdf4c779a8e",
    "nw-proposal-structure": "fbc27cdc2b543abc0d78645495d19123",
    "nw-psychological-safety": "d6e1bfdbd57a4a03c88a797d626532a0",
    "nw-quality-framework": "034dbb86d2258fb31722900b9caa3133",
    "nw-quality-validation": "241512842063a03857ebee3b8cb1f3ce",
    "nw-query-optimization": "c38b238746e7b4a947e4ff289bd19102",
    "nw-research-methodology": "c6703933561dc7a8231b6cdd5bd8f8c9",
    "nw-review-output-format": "b341b4b71fa76d490104320d02a10b38",
    "nw-review-workflow": "e6d0ae79a26fa4fb28ee57858bc59d21",
    "nw-roadmap-design": "5686b164c4c512bba8e6d15390daadc3",
    "nw-roadmap-review-checks": "a203ebf49e2da5d46380a256489b0cb7",
    "nw-rr-critique-dimensions": "8a7f0112b643f3b799136290d72e3ddb",
    "nw-sa-critique-dimensions": "3c93cea879e444fed7e9369ff23178a3",
    "nw-sar-critique-dimensions": "64134d4c75f48c9fb2d7cccdb4f1eea6",
    "nw-sc-review-dimensions": "5fd4e83d9c5a4797afaadd949b3f99cf",
    "nw-sci-fi-design-patterns": "99ca032e5664bfd230ea6deb6a676356",
    "nw-security-and-governance": "a50b88a0d8ba5fdcc595621363e5f82e",
    "nw-security-by-design": "244aa1d801d18000de5fe99cb5da99fb",
    "nw-sequence-design": "00b671455f5078e39dca21c6111c729d",
    "nw-shared-artifact-tracking": "5716e7943fe89af60bc51293fe065ca7",
    "nw-signal-detection": "4dde18d53f6781851f1949f2a12a6aa9",
    "nw-source-verification": "30c29534d1e663128fa55f80a51bb121",
    "nw-stakeholder-engagement": "e969be07cd325c17be5a1d2e9e627884",
    "nw-stress-analysis": "e3c1e4ff73738a43a2d8c34e057c75ba",
    "nw-tbr-methodology": "e498140d1b9cf04b41b32824ec5b4ccb",
    "nw-tdd-methodology": "413bf5f1e26816485ffa84022dae1cc5",
    "nw-tdd-review-enforcement": "940b650d9684ba99594b97f4b61a5cf2",
    "nw-test-design-mandates": "b0252e805e5ee825dc7f213a736a2da7",
    "nw-test-organization-conventions": "dfbce90a434411f40589fb4ae615a7a8",
    "nw-test-refactoring-catalog": "4ba51f92616074130ad325a42ff18006",
    "nw-tlaplus-verification": "2e01e7c934462fbc8abd9dfd9ed93f81",
    "nw-tr-review-criteria": "1d0a4a3eac764ce6ccc7b2b919bc3229",
    "nw-tutorial-structure": "2d20dcdd915da111facadcbd1203d711",
    "nw-usability-engineering": "7a75f00c64695d1359faaf8654992cfe",
    "nw-user-story-mapping": "d1fd4f920dc5677a2772c29a7d1ee9c0",
    "nw-ux-desktop-patterns": "c0179d83ca138bafb9ebfc7168f2de46",
    "nw-ux-emotional-design": "f7b7f2150643a6f021fc86f879903fb5",
    "nw-ux-principles": "5f1e2429b884724981ac9ac74fcb31b9",
    "nw-ux-tui-patterns": "9158e58e84a64320e690da3be5d7c09a",
    "nw-ux-web-patterns": "5e4f0efc8b0d721c88e84cce5af9bda2",
    "nw-voss-negotiation": "d300ff3a28e2726584192e2e672e40e9",
    "nw-wizard-shared-rules": "76572840dc304840143d61e6d69ba8f7",
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
    """Step 02-01: Verify all 127 non-colliding skills are restructured to
    nw-prefixed SKILL.md format."""

    @pytest.mark.parametrize("skill_name", EXPECTED_BULK_SKILLS)
    def test_skill_directory_exists_with_skill_md(self, skill_name: str) -> None:
        """Each non-colliding skill must exist as nw-{name}/SKILL.md."""
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_file.exists(), (
            f"Expected {skill_file.relative_to(SKILLS_DIR)} to exist"
        )

    def test_total_nw_prefixed_skill_count(self) -> None:
        """Total nw-* directories should be 130 (127 bulk + 3 troubleshooter)."""
        nw_dirs = sorted(
            d for d in SKILLS_DIR.iterdir() if d.is_dir() and d.name.startswith("nw-")
        )
        skill_dirs_with_md = [d for d in nw_dirs if (d / "SKILL.md").exists()]
        assert len(skill_dirs_with_md) >= 130, (
            f"Expected >= 130 nw-*/SKILL.md directories, found {len(skill_dirs_with_md)}"
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
