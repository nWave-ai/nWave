"""The files that make up one workspace directory."""

from __future__ import annotations

from pathlib import Path


class Workspace:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.schema_path = directory / "schema.toml"
        self.journal_path = directory / "journal.jsonl"
        self.lock_path = directory / ".lock"
        self.mode_path = directory / "mode"
        self.baseline_path = directory / "baseline.json"
        self.baseline_directory = directory / "baseline"
        self.kit_record_path = directory / "kit.json"
        self.kit_directory = directory / "kit"
        self.kit_skills_directory = self.kit_directory / "skills"
        self.review_path = directory / "review.jsonl"
        self.size_path = directory / "size.json"
        self.answers_path = directory / "answers.json"

    def is_initialized(self) -> bool:
        return self.schema_path.is_file() and self.journal_path.is_file()
