"""Synthesized-transcript commit-context assembler -- RED scaffold (created by DISTILL).

NEW surface for pi-kata-tdd-flow (ADR-PKT-001 KD4). At the ``git commit`` boundary
the pi extension must supply DES context to the UNCHANGED ``subagent-stop`` engine
via the Claude-Code protocol: a one-line JSONL transcript whose first user message
carries the four DES markers, plus ``cwd`` on the stdin payload. This module owns
the marker-exact assembly (SPIKE constraint 2: malformed markers degrade to a
silent non-DES passthrough = allow, so fidelity is essential).

The four markers (verbatim, per ``des.domain.des_marker_parser``):
    <!-- DES-VALIDATION : required -->
    <!-- DES-PROJECT-ID : {kata_id} -->
    <!-- DES-STEP-ID : {step_id} -->
    <!-- DES-PROJECT-ROOT : {project_root} -->

REUSES UNCHANGED: the engine's marker parser + cwd handling (K2).
"""

from __future__ import annotations


__SCAFFOLD__ = True


def build_transcript_content(
    *,
    kata_id: str,
    step_id: str,
    project_root: str,
) -> str:
    """Assemble the first-user-message content carrying the four DES markers.

    The returned string MUST contain all four markers in the exact comment
    syntax the engine's ``DesMarkerParser`` recognizes. ``DES-VALIDATION``
    being malformed degrades the whole transcript to a non-DES passthrough.
    """
    raise AssertionError("Not yet implemented -- RED scaffold")


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
    raise AssertionError("Not yet implemented -- RED scaffold")


def build_subagent_stop_payload(
    *,
    transcript_path: str,
    project_root: str,
) -> dict:
    """Build the ``subagent-stop`` stdin payload (Claude-Code protocol).

    Returns ``{"agent_transcript_path": ..., "cwd": ...}`` -- the engine resolves
    ``effective_cwd = cwd`` and runs ``GitCommitVerifier`` (KD4).
    """
    raise AssertionError("Not yet implemented -- RED scaffold")
