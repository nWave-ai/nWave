"""Architecture test: release-prod.yml rsync MUST exclude mutation-testing data.

Prevents accidental leak of internal mutation reports to public nWave-ai/nwave mirror.
Wired by mutation-testing-automation feature D-8.1.
"""

from pathlib import Path


def test_release_prod_excludes_mutation_data() -> None:
    release_prod = Path(".github/workflows/release-prod.yml").read_text()
    required_rules = (
        "mutation-reports/",
        ".nwave/mutation-reports/",
    )
    for rule in required_rules:
        assert f"--exclude '{rule}'" in release_prod, (
            f"Missing rsync exclusion: '{rule}'. "
            "Mutation reports would leak to public mirror."
        )
