"""Synthesized-transcript commit-context assembler (ADR-PKT-001 KD4).

NEW surface for pi-kata-tdd-flow. At the ``git commit`` boundary the pi extension
must supply DES context to the UNCHANGED ``subagent-stop`` engine via the
Claude-Code protocol: a one-line JSONL transcript whose first user message carries
the four DES markers, plus ``cwd`` on the stdin payload. This module owns the
marker-exact assembly (SPIKE constraint 2: malformed markers degrade to a silent
non-DES passthrough = allow, so fidelity is essential).

The four markers (verbatim, per ``des.domain.des_marker_parser``):
    <!-- DES-VALIDATION : required -->
    <!-- DES-PROJECT-ID : {kata_id} -->
    <!-- DES-STEP-ID : {step_id} -->
    <!-- DES-PROJECT-ROOT : {project_root} -->

This is a PURE assembler: it invents no allow/block verdict; the engine decides.

REUSES UNCHANGED: the engine's marker parser + cwd handling + GitCommitVerifier
(K2 -- zero ``src/des/**`` change).
"""

from __future__ import annotations

import json
from pathlib import Path


_VALIDATION_MARKER = "<!-- DES-VALIDATION : required -->"


def build_transcript_content(
    *,
    kata_id: str,
    step_id: str,
    project_root: str,
) -> str:
    """Assemble the first-user-message content carrying the four DES markers.

    The returned string contains all four markers in the exact comment syntax
    the engine's ``DesMarkerParser`` recognizes. An empty/blank marker value
    (e.g. ``kata_id=""``) yields a marker whose value cannot match ``\\S+``, so
    the engine reads no DES context and degrades to a non-DES passthrough.
    """
    return "\n".join(
        [
            _VALIDATION_MARKER,
            f"<!-- DES-PROJECT-ID : {kata_id} -->",
            f"<!-- DES-STEP-ID : {step_id} -->",
            f"<!-- DES-PROJECT-ROOT : {project_root} -->",
        ]
    )


def write_synthesized_transcript(
    *,
    transcript_path: str,
    kata_id: str,
    step_id: str,
    project_root: str,
) -> None:
    """Write the one-line JSONL synthesized transcript to ``transcript_path``.

    Shape (per ``subagent_stop_handler.extract_des_context_from_transcript``):
        {"message": {"content": "<...four markers...>"}}
    """
    content = build_transcript_content(
        kata_id=kata_id,
        step_id=step_id,
        project_root=project_root,
    )
    target = Path(transcript_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"message": {"content": content}})
    target.write_text(line + "\n", encoding="utf-8")


def build_subagent_stop_payload(
    *,
    transcript_path: str,
    project_root: str,
) -> dict:
    """Build the ``subagent-stop`` stdin payload (Claude-Code protocol).

    Returns ``{"agent_transcript_path": ..., "cwd": ...}`` -- the engine resolves
    ``effective_cwd`` from the validated DES-PROJECT-ROOT marker (falling back to
    ``cwd``) and runs ``GitCommitVerifier`` against the resolved repo (KD4).
    """
    return {
        "agent_transcript_path": transcript_path,
        "cwd": project_root,
    }
