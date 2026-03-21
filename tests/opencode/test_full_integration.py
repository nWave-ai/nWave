"""Full integration tests for the OpenCode DES shim.

Step 02-02: Regression gate + final integration verification.

1. Template rendering produces valid TypeScript with correct Python path
2. Write guard blocks execution-log.json modifications
3. Write guard allows normal file writes
4. Edit guard blocks execution-log.json modifications
"""

import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
ADAPTER_MODULE = "des.adapters.drivers.hooks.claude_code_hook_adapter"
TEMPLATE_PATH = (
    Path(PROJECT_ROOT) / "nWave" / "templates" / "opencode-des-plugin.ts.template"
)


def _run_adapter(
    action: str, stdin_json: dict, env_extra: dict | None = None
) -> subprocess.CompletedProcess:
    """Invoke the Python DES adapter as a subprocess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        [sys.executable, "-m", ADAPTER_MODULE, action],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


class TestTemplateRendering:
    """Verify the TS template renders correctly with placeholder substitution."""

    def test_template_file_exists(self):
        """The TS shim template must exist at the expected path."""
        assert TEMPLATE_PATH.exists(), f"Template not found: {TEMPLATE_PATH}"

    def test_template_renders_with_python_path(self):
        """Template substitution replaces both placeholders correctly."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        python_path = "/usr/bin/python3"
        pythonpath = "$HOME/.claude/lib/python"

        rendered = template.replace("{{PYTHON_PATH}}", python_path)
        rendered = rendered.replace("{{PYTHONPATH}}", pythonpath)

        # Placeholders must be fully substituted
        assert "{{PYTHON_PATH}}" not in rendered
        assert "{{PYTHONPATH}}" not in rendered

        # Rendered content must contain the substituted values
        assert python_path in rendered
        assert pythonpath in rendered

    def test_rendered_template_contains_required_structures(self):
        """Rendered template has all required hook handlers and functions."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        # Must export the default plugin function
        assert "export default function nwaveDES" in template

        # Must register both hook types
        assert '"tool.execute.before"' in template
        assert '"session.created"' in template

        # Must have the translation function
        assert "function translateEvent" in template

        # Must have the adapter invocation function
        assert "function invokeDESAdapter" in template

        # Must have degraded mode warning
        assert "degraded mode" in template.lower()
        assert "5894" in template

    def test_rendered_template_has_valid_typescript_structure(self):
        """Basic structural validation: balanced braces, no template artifacts."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        rendered = template.replace("{{PYTHON_PATH}}", "/usr/bin/python3")
        rendered = rendered.replace("{{PYTHONPATH}}", "/home/user/.claude/lib/python")

        # No unsubstituted template placeholders
        assert "{{" not in rendered
        assert "}}" not in rendered

        # Balanced braces (basic structural check)
        open_braces = rendered.count("{")
        close_braces = rendered.count("}")
        assert open_braces == close_braces, (
            f"Unbalanced braces: {open_braces} open, {close_braces} close"
        )


class TestWriteGuard:
    """Write guard blocks writes to execution-log.json via pre-write action.

    The TS shim translates OC write events to CC Write format and invokes
    the Python adapter with action 'pre-write'. The adapter blocks writes
    to execution-log.json (exit 2) and allows writes to normal files (exit 0).
    """

    def test_write_to_execution_log_blocked(self, tmp_path):
        """Writing to execution-log.json is blocked (exit 2)."""
        # Create a DES project directory with an active execution log
        des_dir = tmp_path / ".des"
        des_dir.mkdir()
        exec_log = des_dir / "execution-log.json"
        exec_log.write_text(
            json.dumps(
                {
                    "schema_version": "4.0",
                    "feature_id": "my-feature",
                    "steps": [
                        {
                            "step_id": "step-01",
                            "name": "Test step",
                            "status": "in_progress",
                            "phases": [],
                        }
                    ],
                }
            )
        )

        cc_json = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(des_dir / "execution-log.json"),
                "content": '{"tampered": true}',
            },
        }

        result = _run_adapter(
            "pre-write",
            cc_json,
            env_extra={"DES_PROJECT_DIR": str(tmp_path)},
        )

        assert result.returncode == 2, (
            f"Write to execution-log.json must be blocked (exit 2), "
            f"got {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_write_to_normal_file_allowed(self, tmp_path):
        """Writing to a normal source file is allowed (exit 0)."""
        cc_json = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/src/user_repository.py",
                "content": "class UserRepo:\n    pass",
            },
        }

        result = _run_adapter(
            "pre-write",
            cc_json,
            env_extra={"DES_PROJECT_DIR": str(tmp_path)},
        )

        assert result.returncode == 0, (
            f"Write to normal file must be allowed (exit 0), "
            f"got {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


class TestEditGuard:
    """Edit guard blocks edits to execution-log.json via pre-write action.

    The TS shim translates OC edit events to CC Edit format and invokes
    the Python adapter with action 'pre-write' (same as write). The adapter
    blocks edits to execution-log.json.
    """

    def test_edit_to_execution_log_blocked(self, tmp_path):
        """Editing execution-log.json is blocked (exit 2)."""
        des_dir = tmp_path / ".des"
        des_dir.mkdir()
        exec_log = des_dir / "execution-log.json"
        exec_log.write_text(
            json.dumps(
                {
                    "schema_version": "4.0",
                    "feature_id": "my-feature",
                    "steps": [
                        {
                            "step_id": "step-01",
                            "name": "Test step",
                            "status": "in_progress",
                            "phases": [],
                        }
                    ],
                }
            )
        )

        cc_json = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(des_dir / "execution-log.json"),
                "old_string": '"status": "in_progress"',
                "new_string": '"status": "completed"',
            },
        }

        result = _run_adapter(
            "pre-write",
            cc_json,
            env_extra={"DES_PROJECT_DIR": str(tmp_path)},
        )

        assert result.returncode == 2, (
            f"Edit to execution-log.json must be blocked (exit 2), "
            f"got {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
