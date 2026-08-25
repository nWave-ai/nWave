"""Focused security regression tests for the skill-hash pre-commit hook."""

from scripts.hooks import validate_skill_hashes


def test_extract_bulk_hashes_accepts_sha256_only(monkeypatch, tmp_path) -> None:
    """A legacy 32-hex digest must not silently re-enable the MD5 path."""
    hash_file = tmp_path / "test_skill_restructuring.py"
    sha256 = "a" * 64
    hash_file.write_text(
        "BULK_HASHES = {\n"
        f'    "nw-current": "{sha256}",\n'
        f'    "nw-legacy": "{"b" * 32}",\n'
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_skill_hashes, "HASH_TEST_FILE", hash_file)

    assert validate_skill_hashes.extract_bulk_hashes() == {"nw-current": sha256}
