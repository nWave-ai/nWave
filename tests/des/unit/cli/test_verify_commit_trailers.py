"""Unit tests for generic HMAC commit-trailer verifier CLI."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from des.cli.verify_commit_trailers import (
    Trailer,
    canonical_verdict_json,
    compute_verdict_hash,
    extract_trailers,
    main,
    verify_trailer,
)


KEY = b"test-signing-key-2026"
AGENT = "nw-software-crafter-reviewer"


def _verdict(text: str = "APPROVED") -> dict[str, object]:
    return {
        "verdict": text,
        "timestamp": "2026-05-19T12:00:00+00:00",
        "reviewer_agent_id": AGENT,
        "findings_summary": ["finding-a", "finding-b"],
    }


def _commit_body(
    verdict: dict[str, object], hash_hex: str, *, agent: str = AGENT
) -> str:
    payload = json.dumps(verdict, sort_keys=True, separators=(",", ":"))
    return (
        "feat(x): example\n"
        "\n"
        "Body line.\n"
        f"Verdict-Payload: {payload}\n"
        f"Reviewed-by: {agent}:{hash_hex}\n"
    )


def _run_with_message(
    message: str,
    *,
    key_env: str | None = None,
    key_file: Path | None = None,
    strict: bool = False,
) -> int:
    argv = ["--commit", "HEAD"]
    if key_env is not None:
        argv += ["--key-env", "TEST_KEY_VAR"]
    if key_file is not None:
        argv += ["--key-file", str(key_file)]
    if strict:
        argv.append("--strict")
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=message, stderr=""
    )
    with patch("des.cli.verify_commit_trailers.subprocess.run", return_value=completed):
        return main(argv=argv)


class TestExtractTrailers:
    def test_extracts_single_trailer(self) -> None:
        msg = f"feat: x\n\nReviewed-by: {AGENT}:" + "ab" * 32 + "\n"
        trailers = extract_trailers(msg)
        assert trailers == [Trailer(agent_id=AGENT, hash_hex="ab" * 32)]

    def test_no_trailers_returns_empty(self) -> None:
        assert extract_trailers("feat: x\n\nbody\n") == []

    def test_malformed_trailer_raises(self) -> None:
        with pytest.raises(ValueError):
            extract_trailers("Reviewed-by: bad-shape-no-colon\n")


class TestCanonicalVerdictJson:
    def test_serialises_sorted_keys_no_whitespace(self) -> None:
        out = canonical_verdict_json(_verdict())
        assert b" " not in out
        # sorted keys: findings_summary < reviewer_agent_id < timestamp < verdict
        assert out.startswith(b'{"findings_summary":')

    def test_rejects_missing_field(self) -> None:
        bad = _verdict()
        del bad["verdict"]
        with pytest.raises(ValueError):
            canonical_verdict_json(bad)

    def test_rejects_extra_field(self) -> None:
        bad = _verdict()
        bad["extra"] = "leak"
        with pytest.raises(ValueError):
            canonical_verdict_json(bad)

    @given(
        text=st.text(min_size=1, max_size=20),
        ts=st.text(min_size=1, max_size=30),
        aid=st.text(min_size=1, max_size=40),
        findings=st.lists(st.text(min_size=0, max_size=20), max_size=5),
    )
    @settings(max_examples=50, deadline=None)
    def test_canonical_invariant_deterministic(
        self, text: str, ts: str, aid: str, findings: list[str]
    ) -> None:
        """Same verdict dict serialises to identical bytes regardless of insertion order."""
        v1 = {
            "verdict": text,
            "timestamp": ts,
            "reviewer_agent_id": aid,
            "findings_summary": findings,
        }
        v2 = {
            "findings_summary": findings,
            "reviewer_agent_id": aid,
            "timestamp": ts,
            "verdict": text,
        }
        assert canonical_verdict_json(v1) == canonical_verdict_json(v2)

    @given(text=st.text(min_size=1, max_size=10))
    @settings(max_examples=30, deadline=None)
    def test_hash_matches_independent_recompute(self, text: str) -> None:
        v = _verdict(text)
        expected = hmac.new(
            KEY,
            json.dumps(v, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert compute_verdict_hash(v, KEY) == expected


class TestVerifyTrailer:
    def test_valid_trailer_verifies(self) -> None:
        v = _verdict()
        h = compute_verdict_hash(v, KEY)
        assert verify_trailer(Trailer(AGENT, h), v, KEY) is True

    def test_tampered_trailer_rejected(self) -> None:
        v = _verdict()
        h = compute_verdict_hash(v, KEY)
        tampered = h[:-2] + ("00" if h[-2:] != "00" else "ff")
        assert verify_trailer(Trailer(AGENT, tampered), v, KEY) is False


class TestMainCli:
    def test_happy_path_exit_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        v = _verdict()
        h = compute_verdict_hash(v, KEY)
        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)
        monkeypatch.delenv("TEST_KEY_VAR", raising=False)
        assert (
            _run_with_message(
                _commit_body(v, h), key_env="TEST_KEY_VAR", key_file=key_file
            )
            == 0
        )

    def test_tampered_trailer_exit_4(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        v = _verdict()
        h = compute_verdict_hash(v, KEY)
        tampered = h[:-2] + ("00" if h[-2:] != "00" else "ff")
        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)
        monkeypatch.delenv("TEST_KEY_VAR", raising=False)
        assert (
            _run_with_message(
                _commit_body(v, tampered), key_env="TEST_KEY_VAR", key_file=key_file
            )
            == 4
        )

    def test_missing_key_exit_5(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        v = _verdict()
        h = compute_verdict_hash(v, KEY)
        monkeypatch.delenv("TEST_KEY_VAR", raising=False)
        assert (
            _run_with_message(
                _commit_body(v, h),
                key_env="TEST_KEY_VAR",
                key_file=tmp_path / "absent.key",
            )
            == 5
        )

    def test_malformed_trailer_exit_6(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)
        monkeypatch.delenv("TEST_KEY_VAR", raising=False)
        msg = "feat: x\n\nReviewed-by: malformed-no-hex\n"
        assert _run_with_message(msg, key_env="TEST_KEY_VAR", key_file=key_file) == 6

    def test_strict_no_trailers_exit_6(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)
        monkeypatch.delenv("TEST_KEY_VAR", raising=False)
        assert (
            _run_with_message(
                "feat: x\n\nbody only\n",
                key_env="TEST_KEY_VAR",
                key_file=key_file,
                strict=True,
            )
            == 6
        )

    def test_no_trailers_default_exit_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(KEY)
        monkeypatch.delenv("TEST_KEY_VAR", raising=False)
        assert (
            _run_with_message(
                "feat: x\n\nbody only\n", key_env="TEST_KEY_VAR", key_file=key_file
            )
            == 0
        )

    def test_env_key_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        v = _verdict()
        h = compute_verdict_hash(v, KEY)
        # File contains wrong key; env contains correct key.
        wrong_file = tmp_path / "wrong.key"
        wrong_file.write_bytes(b"wrong-key")
        monkeypatch.setenv("TEST_KEY_VAR", KEY.decode("utf-8"))
        assert (
            _run_with_message(
                _commit_body(v, h), key_env="TEST_KEY_VAR", key_file=wrong_file
            )
            == 0
        )
