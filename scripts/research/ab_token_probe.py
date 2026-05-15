"""A/B token-cost probe harness.

Empirical gate for token-reduction cuts on agent files (architect + crafter).
Measures input/output/cache tokens of Config A (baseline) vs Config B (with cuts)
on the same task spec, producing a structured comparison with PASS/FAIL verdict.

Hexagonal layout:
- Domain: frozen dataclasses (TokenUsage, ConfigRun, ProbeResult)
- Driving port: `run_probe` function
- Driven ports: `CLIDispatcher`, `ReportWriter` (Protocols)
- Adapters: `ClaudeCLIDispatcher`, `JSONReportWriter`
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from collections.abc import Callable


# ---------------------------------------------------------------------------
# Domain — frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenUsage:
    """Token counts captured from a single CLI run."""

    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


@dataclass(frozen=True)
class ConfigRun:
    """One run of the task under a labelled configuration (A or B)."""

    config_label: str
    task_spec: str
    usage: TokenUsage
    output_text: str
    duration_seconds: float


@dataclass(frozen=True)
class ProbeResult:
    """Comparison of two ConfigRuns with computed deltas and quality verdict."""

    task_spec: str
    run_a: ConfigRun
    run_b: ConfigRun
    delta_input_pct: float
    delta_output_pct: float
    delta_total_pct: float
    quality_verdict: str
    verdict_reason: str


# ---------------------------------------------------------------------------
# Driven ports (Protocols)
# ---------------------------------------------------------------------------


class CLIDispatcher(Protocol):
    """Driven port — invokes the CLI under a given config and returns usage."""

    def dispatch(self, config_label: str, task_spec: str) -> ConfigRun: ...


class ReportWriter(Protocol):
    """Driven port — persists a ProbeResult to a destination path."""

    def write(self, result: ProbeResult, dest: Path) -> None: ...


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def delta_pct(a: int, b: int) -> float:
    """Percentage delta from A to B: (b - a) / a * 100.

    Precondition: a > 0. The probe never compares against a zero-token baseline.
    """
    if a <= 0:
        raise ValueError(f"baseline tokens must be positive, got {a}")
    return (b - a) / a * 100


def default_quality_check(
    run_a: ConfigRun,
    run_b: ConfigRun,
    key_markers: list[str] | None = None,
) -> tuple[str, str]:
    """Default quality gate for B vs A.

    PASS iff:
      - len(b.output_text) >= 0.85 * len(a.output_text)
      - AND every marker in `key_markers` that appears in a.output_text
        also appears in b.output_text

    Otherwise FAIL with a diagnostic reason.
    """
    a_text = run_a.output_text
    b_text = run_b.output_text
    a_len = len(a_text)
    b_len = len(b_text)

    if a_len == 0:
        # Defensive: cannot compare ratios with empty baseline. Treat as INCONCLUSIVE.
        return ("INCONCLUSIVE", "baseline output_text is empty")

    ratio = b_len / a_len
    if ratio < 0.85:
        return (
            "FAIL",
            f"b output_text length {b_len} < 85% of a ({a_len}); ratio={ratio:.2f}",
        )

    markers = key_markers or []
    missing = [m for m in markers if m in a_text and m not in b_text]
    if missing:
        return ("FAIL", f"b output_text missing key markers: {missing}")

    return ("PASS", f"length ratio {ratio:.2f}, all markers preserved")


# ---------------------------------------------------------------------------
# Driving port — `run_probe`
# ---------------------------------------------------------------------------


def _timestamped_dest(dest_dir: Path) -> Path:
    """Build a probe-{timestamp}.json path under dest_dir."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return dest_dir / f"probe-{ts}.json"


def run_probe(
    task_spec: str,
    dispatcher: CLIDispatcher,
    writer: ReportWriter,
    quality_check: Callable[[ConfigRun, ConfigRun], tuple[str, str]],
    dest_dir: Path,
) -> ProbeResult:
    """Run `task_spec` under Config A + B, compute deltas, verify quality, write report.

    Returns the assembled ProbeResult; also persists it to a timestamped JSON
    file under `dest_dir` via the `writer` driven port.
    """
    run_a = dispatcher.dispatch("A", task_spec)
    run_b = dispatcher.dispatch("B", task_spec)

    d_input = delta_pct(run_a.usage.input_tokens, run_b.usage.input_tokens)
    # output_tokens may be 0; protect zero-baseline by treating as 0% delta.
    if run_a.usage.output_tokens > 0:
        d_output = delta_pct(run_a.usage.output_tokens, run_b.usage.output_tokens)
    else:
        d_output = 0.0
    d_total = delta_pct(run_a.usage.total, run_b.usage.total)

    verdict, reason = quality_check(run_a, run_b)

    result = ProbeResult(
        task_spec=task_spec,
        run_a=run_a,
        run_b=run_b,
        delta_input_pct=d_input,
        delta_output_pct=d_output,
        delta_total_pct=d_total,
        quality_verdict=verdict,
        verdict_reason=reason,
    )

    dest = _timestamped_dest(dest_dir)
    writer.write(result, dest)
    return result


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaudeCLIDispatcher:
    """Real CLIDispatcher — invokes `claude --print --output-format=stream-json`.

    Out of scope for harness-build tests (deferred per task brief): real CLI
    dispatch is exercised only on manual invocation. The implementation is
    kept here so the CLI entry-point can wire it; tests use fakes.
    """

    config_dir_a: Path
    config_dir_b: Path

    def dispatch(self, config_label: str, task_spec: str) -> ConfigRun:
        config_dir = {"A": self.config_dir_a, "B": self.config_dir_b}[config_label]
        start = time.monotonic()
        proc = subprocess.run(
            [
                "claude",
                "--print",
                "--output-format=stream-json",
                "--verbose",
                "-p",
                task_spec,
            ],
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(config_dir)},
            capture_output=True,
            text=True,
            check=False,
        )
        duration = time.monotonic() - start
        usage, output_text = _parse_stream_json(proc.stdout)
        return ConfigRun(
            config_label=config_label,
            task_spec=task_spec,
            usage=usage,
            output_text=output_text,
            duration_seconds=duration,
        )


def _parse_stream_json(stdout: str) -> tuple[TokenUsage, str]:
    """Parse NDJSON stream-json output, aggregating usage and assistant text.

    The Claude `--output-format=stream-json` stream emits one JSON object
    per line. Assistant messages carry a `usage` dict per turn and content
    blocks with type=text. We sum usage across turns and concatenate text.
    """
    input_t = output_t = cache_c = cache_r = 0
    text_parts: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = (obj.get("message") or {}).get("usage") or obj.get("usage")
        if isinstance(usage, dict):
            input_t += int(usage.get("input_tokens", 0) or 0)
            output_t += int(usage.get("output_tokens", 0) or 0)
            cache_c += int(usage.get("cache_creation_input_tokens", 0) or 0)
            cache_r += int(usage.get("cache_read_input_tokens", 0) or 0)
        content = (obj.get("message") or {}).get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text", "")))
        elif isinstance(content, str):
            text_parts.append(content)
    return (
        TokenUsage(
            input_tokens=input_t,
            output_tokens=output_t,
            cache_creation_tokens=cache_c,
            cache_read_tokens=cache_r,
        ),
        "".join(text_parts),
    )


@dataclass(frozen=True)
class JSONReportWriter:
    """Real ReportWriter — writes ProbeResult to JSON under dest_dir."""

    def write(self, result: ProbeResult, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "task_spec": result.task_spec,
            "run_a": _run_to_dict(result.run_a),
            "run_b": _run_to_dict(result.run_b),
            "delta_input_pct": result.delta_input_pct,
            "delta_output_pct": result.delta_output_pct,
            "delta_total_pct": result.delta_total_pct,
            "quality_verdict": result.quality_verdict,
            "verdict_reason": result.verdict_reason,
        }
        dest.write_text(json.dumps(payload, indent=2))


def _run_to_dict(run: ConfigRun) -> dict:
    return {
        "config_label": run.config_label,
        "task_spec": run.task_spec,
        "usage": {
            "input_tokens": run.usage.input_tokens,
            "output_tokens": run.usage.output_tokens,
            "cache_creation_tokens": run.usage.cache_creation_tokens,
            "cache_read_tokens": run.usage.cache_read_tokens,
            "total": run.usage.total,
        },
        "output_text": run.output_text,
        "duration_seconds": run.duration_seconds,
    }


# ---------------------------------------------------------------------------
# CLI entry — argparse, dispatch real adapters
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ab_token_probe",
        description=(
            "A/B token-cost probe — compare Config A (baseline) vs Config B "
            "(with cuts applied) on the same task spec."
        ),
    )
    parser.add_argument(
        "--task-spec", required=True, help="Task spec text or file path"
    )
    parser.add_argument(
        "--config-a-dir",
        required=True,
        type=Path,
        help="Path to Config A (baseline) directory",
    )
    parser.add_argument(
        "--config-b-dir",
        required=True,
        type=Path,
        help="Path to Config B (cuts applied) directory",
    )
    parser.add_argument(
        "--dest-dir",
        required=True,
        type=Path,
        help="Directory where the probe report will be written",
    )
    args = parser.parse_args(argv)

    task_spec = args.task_spec
    task_path = Path(task_spec)
    if task_path.is_file():
        task_spec = task_path.read_text()

    dispatcher = ClaudeCLIDispatcher(
        config_dir_a=args.config_a_dir, config_dir_b=args.config_b_dir
    )
    writer = JSONReportWriter()

    result = run_probe(
        task_spec=task_spec,
        dispatcher=dispatcher,
        writer=writer,
        quality_check=default_quality_check,
        dest_dir=args.dest_dir,
    )

    sys.stdout.write(
        json.dumps(
            {
                "verdict": result.quality_verdict,
                "reason": result.verdict_reason,
                "delta_total_pct": result.delta_total_pct,
                "delta_input_pct": result.delta_input_pct,
                "delta_output_pct": result.delta_output_pct,
            },
            indent=2,
        )
        + "\n"
    )
    return 0 if result.quality_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
