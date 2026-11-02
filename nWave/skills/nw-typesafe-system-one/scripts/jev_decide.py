#!/usr/bin/env python3
"""Make one bounded Jev decision and retain its typed result locally.

The caller supplies a small JSON request and chooses where the response is
written.  This program does not infer a decision, retry, or transmit files.

The host may invoke this same CLI with an authorized role-owned request; the
request bytes and successful response bytes are retained unchanged. Privacy,
reviewer reasoning and verdicts remain with the role, not this transport.
Missing capability returns an explicit exit status, never a synthetic judgment.

Wire schema: https://api.typesafe.ai/openapi.json (2026-10-01).
The API specifies approximately normalized probabilities without a precision
bound. We allow 0.01 absolute rounding error for sums and expected scores,
plus floating-point epsilon. Confidence is independent of the distribution.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
_REQUIRED = {"state", "model", "questions"}


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite")
    return number


def _reject_constant(_value: str) -> None:
    raise ValueError("JSON numbers must be finite")


def _decode(body: bytes) -> object:
    return json.loads(
        body.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_float=_finite_float,
        parse_constant=_reject_constant,
    )


def _content(value: object, *, nullable: bool = True) -> bool:
    return isinstance(value, (str, dict, list)) or (nullable and value is None)


def _request_bytes(path: Path) -> bytes:
    try:
        body = sys.stdin.buffer.read() if str(path) == "-" else path.read_bytes()
    except OSError as error:
        raise ValueError(
            "request must be readable, finite, unique-key UTF-8 JSON"
        ) from error
    if not body.strip():
        source = "stdin" if str(path) == "-" else str(path)
        raise ValueError(
            f"request is empty: nothing arrived on {source}. Write the JSON to a file "
            "and pass --request request.json, or pass --request - and end the same "
            "shell command with <<'JSON', then the JSON lines, then a line JSON"
        )
    try:
        payload = _decode(body)
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(
            "request must be readable, finite, unique-key UTF-8 JSON"
        ) from error
    if not isinstance(payload, dict) or set(payload) != _REQUIRED:
        raise ValueError("request has exactly state, model, and questions")
    if not _content(payload["state"], nullable=False):
        raise ValueError("state is a string, object, or array")
    if not isinstance(payload["model"], str) or not payload["model"].strip():
        raise ValueError("model is a non-empty string")
    questions = payload["questions"]
    if not isinstance(questions, dict) or not questions:
        raise ValueError("questions is a non-empty object")
    for identifier, question in questions.items():
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("each question has a non-empty string identifier")
        if not isinstance(question, dict):
            raise ValueError(f"question {identifier!r} is an object")
        if set(question) - {"type", "instructions", "criteria"}:
            raise ValueError(f"question {identifier!r} has unsupported fields")
        kind = question.get("type")
        if kind not in ("choice", "score", "noul"):
            raise ValueError(f"question {identifier!r} type is choice, score, or noul")
        if not _content(question.get("instructions")):
            raise ValueError(f"question {identifier!r} instructions have invalid type")
        criteria = question.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not all(
                _content(value) for value in criteria.values()
            ):
                raise ValueError(
                    f"question {identifier!r} choice criteria is an object"
                )
        elif kind == "score":
            if (
                not isinstance(criteria, list)
                or not criteria
                or not all(_content(value, nullable=False) for value in criteria)
            ):
                raise ValueError(
                    f"question {identifier!r} score criteria is a non-empty ordered array"
                )
        elif criteria is not None:
            if (
                not isinstance(criteria, dict)
                or set(criteria) - {"true", "false"}
                or not all(_content(value) for value in criteria.values())
            ):
                raise ValueError(
                    f"question {identifier!r} noul criteria uses true and false"
                )
    return body


def _number(value: object, lower: float, upper: float, field: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not lower <= value <= upper
    ):
        raise ValueError(f"{field} must be a finite number in [{lower}, {upper}]")


def _distribution(answer: dict, labels: set[str], field: str) -> dict:
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != labels:
        raise ValueError(f"{field} probabilities must match requested criteria")
    for probability in probabilities.values():
        _number(probability, 0, 1, f"{field} probability")
    if not math.isclose(
        sum(probabilities.values()), 1, rel_tol=0, abs_tol=0.010000000001
    ):
        raise ValueError(f"{field} probabilities must sum approximately to 1")
    return probabilities


def _validate_response(payload: object, questions: dict) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
        raise ValueError("response has no typed answers")
    answers = payload["answers"]
    if set(answers) != set(questions):
        raise ValueError("response answers must match question identifiers exactly")
    if not isinstance(payload.get("model"), str) or not payload["model"].strip():
        raise ValueError("response model must be a non-empty string")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("response usage is required")
    for field in ("input_tokens", "output_tokens"):
        value = usage.get(field)
        if type(value) is not int or value < 0:
            raise ValueError(f"response usage {field} must be a nonnegative integer")
    for identifier, question in questions.items():
        answer = answers[identifier]
        field = f"answer {identifier!r}"
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError(f"{field} type must match question type {kind}")
        if kind == "noul":
            _number(answer.get("noul"), 0, 1, f"{field} noul")
            continue
        _number(answer.get("confidence"), 0, 1, f"{field} confidence")
        criteria = question["criteria"]
        labels = (
            set(criteria)
            if kind == "choice"
            else {str(i) for i in range(len(criteria))}
        )
        probabilities = _distribution(answer, labels, field)
        if kind == "choice":
            choice = answer.get("choice")
            if not isinstance(choice, str) or choice not in labels:
                raise ValueError(f"{field} choice must be a requested label")
            if probabilities[choice] != max(probabilities.values()):
                raise ValueError(f"{field} choice must have highest probability")
        else:
            legend = {str(i): level for i, level in enumerate(criteria)}
            if answer.get("legend") != legend:
                raise ValueError(f"{field} legend must match ordered criteria")
            score = answer.get("score")
            _number(score, 0, len(criteria) - 1, f"{field} score")
            expected = sum(i * probabilities[str(i)] for i in range(len(criteria)))
            if not math.isclose(score, expected, rel_tol=0, abs_tol=0.010000000001):
                raise ValueError(
                    f"{field} score must match probability-weighted levels"
                )


def _write(path: Path, body: bytes) -> None:
    if str(path) == "-":
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _exit_code_for_http_error(status_code: int) -> int:
    """Map HTTP status to exit code: caller error, access, transient, or service."""
    if status_code in (400, 422):
        return 2  # Malformed request (caller schema)
    if status_code in (401, 403):
        return 5  # Access or configuration
    if status_code in (408, 429) or 500 <= status_code < 600:
        return 3  # Transient (retry later)
    return 4  # Other HTTP failure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--request", required=True, type=Path, help="request JSON file, or - for stdin"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="result JSON file, or - for stdout"
    )
    parser.add_argument(
        "--endpoint", default=os.environ.get("TYPESAFE_BASE_URL", _ENDPOINT)
    )
    args = parser.parse_args(argv)

    # Diagnose caller defects even when the remote capability is absent.
    try:
        body = _request_bytes(args.request)
    except ValueError as error:
        print(f"typesafe: invalid request ({error})", file=sys.stderr)
        return 2
    questions = _decode(body)["questions"]
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        print(
            "typesafe: unavailable (TYPESAFE_API_KEY is absent from this process "
            "environment. A tool kernel, such as a Python eval kernel, may not inherit "
            "the session environment: run this client from a shell command instead)",
            file=sys.stderr,
        )
        return 3

    request = Request(
        args.endpoint,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
    except HTTPError as error:
        exit_code = _exit_code_for_http_error(error.code)
        print(f"typesafe: HTTP {error.code}; no retry was attempted", file=sys.stderr)
        return exit_code
    except TimeoutError:
        print("typesafe: unavailable (network timeout)", file=sys.stderr)
        return 3
    except (URLError, OSError):
        print("typesafe: unavailable (network failure)", file=sys.stderr)
        return 3
    try:
        decoded = _decode(response_body)
    except (ValueError, UnicodeDecodeError):
        print("typesafe: invalid response JSON", file=sys.stderr)
        return 4
    try:
        _validate_response(decoded, questions)
    except ValueError as error:
        print(f"typesafe: invalid response ({error})", file=sys.stderr)
        return 4
    _write(args.output, response_body)
    print(
        f"typesafe: recorded {args.output}",
        file=sys.stderr if str(args.output) == "-" else sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
