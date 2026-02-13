#!/usr/bin/env python3
"""
Discovery Hook for SubagentStop Event

Purpose: Capture and log the ACTUAL context received by SubagentStop hooks
to validate design assumptions for the Deterministic Execution System (DES).

This is a DISCOVERY tool, not a production hook.

Usage:
1. Add to .claude/settings.local.json:
   {
     "hooks": {
       "SubagentStop": [{
         "hooks": [{
           "type": "command",
           "command": "python3 nWave/hooks/discover_subagent_context.py"
         }]
       }]
     }
   }

2. Run any Task tool invocation
3. Check output at: .git/des-discovery/subagent_context.jsonl

Expected Input (from Claude Code documentation):
{
  "session_id": "string",
  "transcript_path": "string",
  "cwd": "string",
  "permission_mode": "string",
  "hook_event_name": "SubagentStop",
  "stop_hook_active": boolean
}

Questions to Answer:
- Q1: What fields are actually present?
- Q2: Is the agent's prompt included?
- Q3: Is the transcript accessible?
- Q4: Can we identify which step file was being processed?
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_discovery_dir() -> Path:
    """Get or create discovery output directory."""
    # Use CLAUDE_PROJECT_DIR if available, otherwise cwd
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    discovery_dir = Path(project_dir) / ".git" / "des-discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    return discovery_dir


def capture_environment() -> dict:
    """Capture relevant environment variables."""
    relevant_vars = [
        "CLAUDE_PROJECT_DIR",
        "CLAUDE_ENV_FILE",
        "CLAUDE_CODE_REMOTE",
        "HOME",
        "USER",
        "PWD",
        "PATH",
    ]

    env_capture = {}
    for var in relevant_vars:
        value = os.environ.get(var)
        if value:
            # Truncate long values like PATH
            if len(value) > 200:
                value = value[:200] + "...[truncated]"
            env_capture[var] = value

    # Also capture any CLAUDE_* variables we might not know about
    for key, value in os.environ.items():
        if key.startswith("CLAUDE_") and key not in env_capture:
            env_capture[key] = value[:200] if len(value) > 200 else value

    return env_capture


def read_stdin_safely() -> tuple[str, dict | None, str | None]:
    """
    Read stdin and attempt to parse as JSON.

    Returns:
        (raw_input, parsed_json_or_none, error_message_or_none)
    """
    try:
        raw_input = sys.stdin.read()
    except Exception as e:
        return "", None, f"Failed to read stdin: {e}"

    if not raw_input or not raw_input.strip():
        return raw_input, None, "stdin was empty"

    try:
        parsed = json.loads(raw_input)
        return raw_input, parsed, None
    except json.JSONDecodeError as e:
        return raw_input, None, f"JSON parse error: {e}"


def check_transcript_accessibility(transcript_path: str | None) -> dict:
    """
    Check if the transcript file exists and is readable.
    Sample first and last entries if accessible.
    """
    result = {
        "path": transcript_path,
        "exists": False,
        "readable": False,
        "size_bytes": None,
        "line_count": None,
        "first_entry_sample": None,
        "last_entry_sample": None,
        "error": None,
    }

    if not transcript_path:
        result["error"] = "No transcript path provided"
        return result

    path = Path(transcript_path).expanduser()
    result["path_expanded"] = str(path)
    result["exists"] = path.exists()

    if not path.exists():
        result["error"] = "File does not exist"
        return result

    try:
        result["size_bytes"] = path.stat().st_size

        with open(path, "r") as f:
            lines = f.readlines()
            result["line_count"] = len(lines)

            if lines:
                # Sample first entry
                try:
                    first = json.loads(lines[0])
                    result["first_entry_sample"] = {
                        "keys": list(first.keys()),
                        "type": first.get("type"),
                    }
                except Exception:
                    result["first_entry_sample"] = {"raw": lines[0][:200]}

                # Sample last entry
                try:
                    last = json.loads(lines[-1])
                    result["last_entry_sample"] = {
                        "keys": list(last.keys()),
                        "type": last.get("type"),
                    }
                except Exception:
                    result["last_entry_sample"] = {"raw": lines[-1][:200]}

        result["readable"] = True

    except Exception as e:
        result["error"] = f"Read error: {e}"

    return result


def main():
    """
    Main discovery function.

    Captures everything we can about the SubagentStop context
    and writes to a discovery log file.
    """
    timestamp = datetime.now().isoformat()
    discovery_dir = get_discovery_dir()

    # Read stdin
    raw_input, parsed_input, parse_error = read_stdin_safely()

    # Capture environment
    env_vars = capture_environment()

    # Check transcript if path provided
    transcript_path = None
    transcript_info = None
    if parsed_input:
        transcript_path = parsed_input.get("transcript_path")
        transcript_info = check_transcript_accessibility(transcript_path)

    # Build discovery record
    discovery_record = {
        "discovery_timestamp": timestamp,
        "discovery_version": "1.0",
        # Raw input analysis
        "stdin": {
            "raw_length": len(raw_input),
            "raw_sample": raw_input[:2000] if raw_input else "(empty)",
            "parse_error": parse_error,
            "parsed_successfully": parsed_input is not None,
        },
        # Parsed input (if successful)
        "hook_input": parsed_input,
        # Schema discovery
        "schema_discovery": {
            "top_level_keys": list(parsed_input.keys()) if parsed_input else [],
            "key_types": {k: type(v).__name__ for k, v in (parsed_input or {}).items()},
        },
        # Environment analysis
        "environment": env_vars,
        # Transcript analysis
        "transcript": transcript_info,
        # Key questions answered
        "questions_answered": {
            "Q1_fields_present": list(parsed_input.keys())
            if parsed_input
            else "UNKNOWN - parse failed",
            "Q2_prompt_included": "prompt" in (parsed_input or {}),
            "Q3_transcript_accessible": transcript_info.get("readable", False)
            if transcript_info
            else False,
            "Q4_step_file_identifiable": _check_step_file_identifiable(
                parsed_input, transcript_info
            ),
        },
    }

    # Write to discovery log (append mode, one JSON per line)
    log_file = discovery_dir / "subagent_context.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(discovery_record) + "\n")

    # Also write latest as readable JSON for quick inspection
    latest_file = discovery_dir / "latest_discovery.json"
    with open(latest_file, "w") as f:
        json.dump(discovery_record, f, indent=2)

    # Write a human-readable summary
    summary_file = discovery_dir / "discovery_summary.md"
    _write_summary(summary_file, discovery_record)

    # Return success - allow subagent to stop normally
    # We're just observing, not blocking
    print(json.dumps({"continue": True}))
    sys.exit(0)


def _check_step_file_identifiable(
    parsed_input: dict | None, transcript_info: dict | None
) -> str:
    """Check if we can identify which step file was being processed."""
    if not parsed_input:
        return "UNKNOWN - no parsed input"

    # Check if prompt contains DES markers
    prompt = parsed_input.get("prompt", "")
    if "DES-STEP-FILE:" in str(prompt):
        return "YES - via DES marker in prompt"

    # Check if transcript is accessible and might contain step file reference
    if transcript_info and transcript_info.get("readable"):
        return "MAYBE - transcript accessible, would need to search"

    return "NO - no obvious mechanism found"


def _write_summary(path: Path, record: dict) -> None:
    """Write human-readable summary of discovery."""
    summary = f"""# SubagentStop Hook Discovery Summary

**Timestamp:** {record["discovery_timestamp"]}

## Questions Answered

| Question | Answer |
|----------|--------|
| Q1: Fields present | {record["questions_answered"]["Q1_fields_present"]} |
| Q2: Prompt included | {record["questions_answered"]["Q2_prompt_included"]} |
| Q3: Transcript accessible | {record["questions_answered"]["Q3_transcript_accessible"]} |
| Q4: Step file identifiable | {record["questions_answered"]["Q4_step_file_identifiable"]} |

## Hook Input Schema

**Top-level keys:** {record["schema_discovery"]["top_level_keys"]}

**Key types:**
```json
{json.dumps(record["schema_discovery"]["key_types"], indent=2)}
```

## Raw Input Sample

```
{record["stdin"]["raw_sample"][:500]}
```

## Environment Variables

```json
{json.dumps(record["environment"], indent=2)}
```

## Transcript Analysis

```json
{json.dumps(record["transcript"], indent=2) if record["transcript"] else "N/A"}
```

---
*Generated by discover_subagent_context.py*
"""
    with open(path, "w") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
