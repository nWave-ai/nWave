"""Reads the TOML schema into domain objects. Every malformed declaration is refused, never guessed."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.refusal import Refusal
from nwstep.domain.retired_schema import retired_name
from nwstep.domain.schema import Schema
from nwstep.domain.size import Size
from nwstep.domain.step import Step


TOP_KEYS = frozenset({"step"})
STEP_KEYS = frozenset(
    {
        "id",
        "title",
        "help",
        "needs",
        "repeat",
        "replay",
        "verdict",
        "prereview",
        "field",
        "skills",
        "sizes",
        "pauses",
    }
)
RESERVED_FIELD_NAMES = frozenset({"item", "root", "workspace"})
FIELD_KEYS = frozenset(
    {
        "name",
        "kind",
        "help",
        "required",
        "choices",
        "min_items",
        "max_items",
        "min_chars",
        "expect",
        "covers",
        "covers_sentences",
        "cross_with",
        "categories",
        "needs_ids",
        "prefix_ids",
        "ids",
        "evidence_chars",
        "decides",
        "contract",
        "locator_ids",
        "verifies",
        "after_craft",
        "runs_on",
        "generated",
        "predicted_by",
        "decided_by",
        "checked_claims",
        "review",
        "must_fail",
        "names_tests",
        "compare_baseline",
        "fallback",
        "required_sizes",
    }
)


class TomlSchemaReader:
    def read(self, path: Path) -> Schema:
        try:
            content = path.read_bytes()
        except OSError as error:
            raise self._invalid(f"{path} cannot be read as TOML: {error}") from None
        retired = retired_name(content)
        if retired is not None:
            raise self._retired(retired)
        try:
            data = tomllib.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise self._invalid(f"{path} cannot be read as TOML: {error}") from None
        self._only_keys(data, TOP_KEYS, "the schema")
        entries = data.get("step")
        if not isinstance(entries, list) or not entries:
            raise self._invalid("the schema needs at least one [[step]] table")
        steps = tuple(self._step(entry) for entry in entries)
        try:
            return Schema(steps)
        except ValueError as error:
            raise self._invalid(str(error)) from None

    def _step(self, entry: Any) -> Step:
        self._only_keys(entry, STEP_KEYS, "a [[step]] table")
        fields = tuple(self._field(item) for item in self._tables(entry, "field"))
        try:
            return Step(
                self._text(entry, "id"),
                self._text(entry, "title"),
                self._text(entry, "help"),
                needs=self._texts(entry, "needs"),
                repeat=self._flag(entry, "repeat", default=False),
                replay=self._flag(entry, "replay", default=False),
                verdict=self._flag(entry, "verdict", default=False),
                prereview=self._flag(entry, "prereview", default=False),
                fields=fields,
                skills=self._texts(entry, "skills"),
                sizes=self._sizes(entry, "sizes"),
                pauses=self._sizes(entry, "pauses") or (),
            )
        except ValueError as error:
            raise self._invalid(str(error)) from None

    def _field(self, entry: Any) -> Field:
        self._only_keys(entry, FIELD_KEYS, "a [[step.field]] table")
        name = self._text(entry, "name")
        if name in RESERVED_FIELD_NAMES:
            raise self._invalid(
                f"field name '{name}' is reserved for the command line; choose another name"
            )
        kind_name = self._text(entry, "kind")
        try:
            kind = FieldKind(kind_name)
        except ValueError:
            raise self._invalid(
                f"field kind '{kind_name}' is unknown; use text, list, enum, int, bool, paths, command, cases, scenarios, conflicts or typesafe"
            ) from None
        try:
            return Field(
                name,
                kind,
                self._text(entry, "help"),
                required=self._flag(entry, "required", default=True),
                choices=self._texts(entry, "choices"),
                min_items=self._number(entry, "min_items"),
                max_items=self._number(entry, "max_items"),
                min_chars=self._number(entry, "min_chars"),
                expect=self._optional_text(entry, "expect"),
                covers=self._optional_text(entry, "covers"),
                covers_sentences=self._optional_text(entry, "covers_sentences"),
                cross_with=self._optional_text(entry, "cross_with"),
                categories=self._texts(entry, "categories"),
                needs_ids=self._optional_text(entry, "needs_ids"),
                prefix_ids=self._flag(entry, "prefix_ids", default=False),
                ids=self._ids(entry),
                evidence_chars=self._number(entry, "evidence_chars"),
                decides=self._optional_text(entry, "decides"),
                contract=self._optional_text(entry, "contract"),
                locator_ids=self._csv(entry, "locator_ids"),
                verifies=self._csv(entry, "verifies"),
                after_craft=self._flag(entry, "after_craft", default=False),
                runs_on=self._optional_text(entry, "runs_on"),
                generated=self._flag(entry, "generated", default=False),
                predicted_by=self._optional_text(entry, "predicted_by"),
                decided_by=self._optional_text(entry, "decided_by"),
                checked_claims=self._flag(entry, "checked_claims", default=False),
                review=self._flag(entry, "review", default=False),
                must_fail=self._csv(entry, "must_fail"),
                names_tests=self._flag(entry, "names_tests", default=False),
                compare_baseline=self._flag(entry, "compare_baseline", default=False),
                fallback=self._optional_text(entry, "fallback"),
                required_sizes=self._sizes(entry, "required_sizes") or (),
            )
        except ValueError as error:
            raise self._invalid(str(error)) from None

    def _tables(self, entry: dict[str, Any], key: str) -> list[Any]:
        value = entry.get(key, [])
        if not isinstance(value, list):
            raise self._invalid(f"'{key}' must be a list of tables")
        return value

    def _text(self, entry: dict[str, Any], key: str) -> str:
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            raise self._invalid(f"'{key}' must be a non-empty string")
        return value

    def _optional_text(self, entry: dict[str, Any], key: str) -> str | None:
        return None if key not in entry else self._text(entry, key)

    def _sizes(self, entry: dict[str, Any], key: str) -> tuple[Size, ...] | None:
        """The sizes a key names, each one of S, M or L; None when the key is absent."""
        if key not in entry:
            return None
        labels = self._texts(entry, key)
        for label in labels:
            if label not in Size.LABELS:
                raise self._invalid(
                    f"'{key}' names the size '{label}', which is not one of {', '.join(Size.LABELS)}"
                )
        return tuple(Size(label) for label in labels)

    def _texts(self, entry: dict[str, Any], key: str) -> tuple[str, ...]:
        value = entry.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise self._invalid(f"'{key}' must be a list of strings")
        return tuple(value)

    def _flag(self, entry: dict[str, Any], key: str, *, default: bool) -> bool:
        value = entry.get(key, default)
        if not isinstance(value, bool):
            raise self._invalid(f"'{key}' must be true or false")
        return value

    def _number(self, entry: dict[str, Any], key: str) -> int | None:
        if key not in entry:
            return None
        value = entry[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise self._invalid(f"'{key}' must be an integer")
        return value

    def _ids(self, entry: dict[str, Any]) -> tuple[str, ...]:
        return self._csv(entry, "ids")

    def _csv(self, entry: dict[str, Any], key: str) -> tuple[str, ...]:
        if key not in entry:
            return ()
        raw = self._text(entry, key)
        return tuple(part.strip() for part in raw.split(",") if part.strip())

    def _only_keys(self, table: Any, allowed: frozenset[str], where: str) -> None:
        if not isinstance(table, dict):
            raise self._invalid(f"{where} must be a table")
        for key in table:
            if key not in allowed:
                raise self._invalid(
                    f"{where} has unknown key '{key}'; allowed keys: {', '.join(sorted(allowed))}"
                )

    @staticmethod
    def _retired(name: str) -> Refusal:
        return Refusal(
            what=f"the schema {name} of this workspace is no longer distributed",
            why="the older schema versions were removed from the checkout; only the shipped schemas are read",
            how=f"read this workspace with an earlier nwave-ai release that still ships {name}, or redo the delivery with dynamic-v10.toml: nwstep init --schema <checkout>/scripts/dev/nwstep/schemas/dynamic-v10.toml --workspace <new directory>",
        )

    @staticmethod
    def _invalid(message: str) -> Refusal:
        return Refusal(
            what=f"schema is invalid: {message}",
            why="every record is checked against the schema copied at init, so a wrong declaration would be enforced wrongly",
        )
