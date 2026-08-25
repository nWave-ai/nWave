"""Focused tests for installer content equality hashing."""

import hashlib

from scripts.install.install_nwave import _file_sha256, _files_content_equal


def test_equal_bytes_have_equal_sha256_and_changed_bytes_are_drift(tmp_path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_bytes(b"same-content")
    target.write_bytes(b"same-content")

    assert _file_sha256(source) == hashlib.sha256(b"same-content").hexdigest()
    assert _files_content_equal(source, target)

    target.write_bytes(b"changed-content")

    assert not _files_content_equal(source, target)
