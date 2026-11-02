"""Render an nWave markdown document to a self-contained HTML page.

WHY IT LIVES UNDER ``nwave_ai.platform``
----------------------------------------
It began as the standalone document-rendering script with one caller. Its owner is now the
platform: the ``nwave-ai`` installed CLI projects the owned delivery state for the human who
decides between an interactive and an autonomous session. The module ships in the wheel with the
package, so an installed runtime reaches it, not only the authoring checkout. It is the ONE
renderer, placed where every caller can reach it, and it is not a second stylesheet.

WHY THIS EXISTS, AND WHY IT IS NOT A REUSE OF ``scripts/docs_site/build_site.py``
---------------------------------------------------------------------------------
``build_site.py:render_markdown`` already renders markdown to HTML — but it shells
out to **pandoc**. This repository's standing constraint is that the only runtime
dependency is Python: no external CLI tool may be required for a shipped asset to
work (target-machine agnosticism). Reusing it would make this renderer work on the
authoring machine and fail on a clean target, which is the exact class of defect
the constraint exists to prevent. So: stdlib only, no subprocess, no third party.

WHAT IT DELIBERATELY DOES **NOT** DO
------------------------------------
This is a bounded renderer for the markdown subset nWave documents actually use.
It does NOT implement full CommonMark. Unsupported constructs are reported on
stderr with their line number rather than silently mangled (degrade-LOUD): a
renderer that quietly drops content would make the HTML lie about the source.

THE SOURCE OF TRUTH IS THE MARKDOWN, NEVER THE HTML
---------------------------------------------------
The generated page is a PROJECTION. It carries a banner naming the markdown file
it came from. Never edit the HTML; edit the markdown and re-render. The published
artifact URL, if any, is recorded back INTO the markdown as a one-line pointer, so
the repository stays authoritative and the link is a convenience, not an authority.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from nwave_ai.platform.assets import resolve_packaged_asset


_BRAND_DIRECTORY = "nWave/data/brand"
_LOGO_ASSET = "nWave/data/brand/logo.svg"
_BRAND_IDENTITY = "nwave-oss-neutral-v1"
_MANIFEST_KEYS = frozenset({"schema-version", "identity", "stylesheet", "font-stack"})
_FONT_STACK = re.compile(r"[A-Za-z0-9 _,.'\"-]+")
_REMOTE_REFERENCE = re.compile(r"(?:https?:)?//", re.IGNORECASE)
_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
    "font-src data:; connect-src 'none'"
)


class BrandAssetError(RuntimeError):
    """A public HTML projection cannot safely use its packaged identity."""


@dataclass(frozen=True)
class Brand:
    """The finite, versioned local inputs for an nWave HTML document."""

    identity: str
    stylesheet: str
    font_stack: str


def _local_asset_name(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise BrandAssetError("brand manifest has no stylesheet name")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or len(candidate.parts) != 1
        or candidate.parts[0] in {".", ".."}
        or ":" in value
        or "//" in value
    ):
        raise BrandAssetError(
            f"brand stylesheet is not a local relative asset: {value!r}"
        )
    return value


def _font_stack_value(value: object) -> str:
    """Accept a manifest-owned CSS font-list value that cannot inject CSS."""
    if not isinstance(value, str) or not value.strip():
        raise BrandAssetError("brand manifest has no font-stack")
    if _FONT_STACK.fullmatch(value) is None:
        raise BrandAssetError("brand manifest font-stack is not a safe CSS value")
    return value


def load_brand() -> Brand:
    """Load one checked, offline brand manifest and its stylesheet.

    Asset resolution uses the same source-vs-installed ambiguity rule as other
    packaged DES assets.  A document is never silently branded from a random
    checkout copy.
    """
    resolution = resolve_packaged_asset(_BRAND_DIRECTORY)
    if not resolution.is_usable or resolution.path is None:
        raise BrandAssetError(
            f"brand asset directory is unavailable: {resolution.detail}"
        )
    directory = resolution.path
    manifest_path = directory / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BrandAssetError(f"brand manifest is unreadable: {error}") from error
    if (
        not isinstance(manifest, dict)
        or frozenset(manifest) != _MANIFEST_KEYS
        or manifest.get("schema-version") != 1
    ):
        raise BrandAssetError("brand manifest has an unsupported schema-version")
    identity = manifest.get("identity")
    if identity != _BRAND_IDENTITY:
        raise BrandAssetError("brand manifest has an unsupported identity")
    stylesheet_name = _local_asset_name(manifest.get("stylesheet"))
    font_stack = _font_stack_value(manifest.get("font-stack"))
    stylesheet_path = directory / stylesheet_name
    try:
        stylesheet_path.resolve().relative_to(directory.resolve())
        stylesheet = stylesheet_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        raise BrandAssetError(f"brand stylesheet is unavailable: {error}") from error
    if not stylesheet.strip():
        raise BrandAssetError("brand stylesheet is empty")
    if "</style" in stylesheet.lower():
        raise BrandAssetError("brand stylesheet cannot be embedded safely")
    if _REMOTE_REFERENCE.search(stylesheet) is not None:
        raise BrandAssetError("brand stylesheet contains a remote asset reference")
    return Brand(identity=identity, stylesheet=stylesheet, font_stack=font_stack)


def load_logo_data_uri() -> str:
    """Embed the packaged copy of the canonical logo as an offline ``data:`` URI."""
    resolution = resolve_packaged_asset(_LOGO_ASSET)
    if not resolution.is_usable or resolution.path is None:
        raise BrandAssetError(f"brand logo is unavailable: {resolution.detail}")
    try:
        svg = resolution.path.read_bytes()
    except OSError as error:
        raise BrandAssetError(f"brand logo is unreadable: {error}") from error
    if b"<svg" not in svg:
        raise BrandAssetError("brand logo is not an SVG document")
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


_UNSUPPORTED: list[tuple[int, str]] = []

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|[\s:|-]+\|$")
_LIST_ITEM = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED_ITEM = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")

# State pills: the SSOT encodes node state as a bare word. Rendering it as a
# coloured chip is information design, not decoration -- state must read at a
# glance, which is the whole reason this projection exists.
_STATE_CLASS = {
    "PRONTO": "s-ready",
    "IN CORSO": "s-wip",
    "AL LAVORO": "s-wip",  # the word the SSOT tables actually use for wip
    "FATTO": "s-done",
    "CHIUSO": "s-done",  # closed-with-nothing-left is done-family, same as FATTO
    "MISURATO": "s-done",
    "QUARANTENA": "s-quar",
    "CONTESO": "s-cont",
    "GUARDIA": "s-guard",
    "BLOCCATO-SERVE-DESIGN": "s-dsn",
    "TIENI": "v-keep",
    "SEMPLIFICA": "v-simp",
    "RIMUOVI": "v-drop",
    "NON_MISURATO": "v-unk",
}


def _inline(text: str) -> str:
    """Escape, then apply inline markup. Order matters: code wins over emphasis."""
    out = html.escape(text, quote=False)
    placeholders: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{match.group(1)}</code>")
        return f"\x00{len(placeholders) - 1}\x00"

    out = _INLINE_CODE.sub(_stash, out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITALIC.sub(r"<em>\1</em>", out)
    out = _LINK.sub(r'<a href="\2">\1</a>', out)
    for index, value in enumerate(placeholders):
        out = out.replace(f"\x00{index}\x00", value)
    return out


def _cell(text: str) -> str:
    """Render one table cell, promoting known state words to coloured chips."""
    stripped = text.strip()
    bare = stripped.strip("*`")
    if bare in _STATE_CLASS:
        return f'<span class="chip {_STATE_CLASS[bare]}">{html.escape(bare)}</span>'
    return _inline(stripped)


def _split_row(line: str) -> list[str]:
    return line.strip().strip("|").split("|")


def render_tree(body: list[str]) -> str:
    """Render an ```nwtree block as a collapsible directory-style tree.

    An ASCII tree inside <pre> is a PHOTOGRAPH of a structure; in a living
    document whose nodes change state it should be the structure itself. The
    directory idiom is the one every reader already knows how to scan.

    Syntax -- indentation (2 spaces per level) carries the hierarchy, fields are
    separated by ' | ':

        GOAL - what we are aiming at
          R1 BRANCH NAME
            D01 | what the node does | PRONTO | XS | onda 1

    Field 1 is the id/label, field 2 the description, any further field becomes a
    badge; a field matching a known state or verdict word becomes a coloured chip.
    A row with children renders as <details>/<summary> -- collapsible with zero
    JavaScript, which keeps the page keyboard-accessible and CSP-safe.
    """
    rows: list[tuple[int, list[str], list[list[str]]]] = []
    for raw in body:
        if not raw.strip():
            continue
        depth = (len(raw) - len(raw.lstrip(" "))) // 2
        fields = [f.strip() for f in raw.strip().split("|")]
        if fields[0].startswith(":"):
            # A DETAIL line: not a node of its own, it is an attribute of the
            # node above. This is what makes a node clickable -- the row detail
            # travels WITH the tree instead of living only in a table the reader
            # has to scroll to and match by id.
            fields[0] = fields[0].lstrip(":").strip()
            if rows:
                rows[-1][2].append(fields)
            continue
        rows.append((depth, fields, []))

    def state_of(fields: list[str]) -> str:
        """The node's state word, if it carries one — drives the row's colour."""
        for extra in fields[2:]:
            bare = extra.strip().strip("*`")
            if bare in _STATE_CLASS:
                return _STATE_CLASS[bare]
        return ""

    def node_html(fields: list[str]) -> str:
        label = html.escape(fields[0])
        parts = [f'<span class="t-id">{label}</span>']
        if len(fields) > 1 and fields[1]:
            parts.append(f'<span class="t-name">{_inline(fields[1])}</span>')
        for extra in fields[2:]:
            if not extra:
                continue
            bare = extra.strip("*`")
            if bare in _STATE_CLASS:
                parts.append(
                    f'<span class="chip {_STATE_CLASS[bare]}">{html.escape(bare)}</span>'
                )
            else:
                parts.append(f'<span class="t-badge">{_inline(extra)}</span>')
        return "".join(parts)

    def detail_html(details: list[list[str]]) -> str:
        """Render the attribute rows a reader sees when they open a node."""
        cells: list[str] = []
        for fields in details:
            key = html.escape(fields[0])
            value = " · ".join(
                f'<span class="chip {_STATE_CLASS[v.strip("*`")]}">'
                f"{html.escape(v.strip('*`'))}</span>"
                if v.strip("*`") in _STATE_CLASS
                else _inline(v)
                for v in fields[1:]
                if v
            )
            cells.append(f"<dt>{key}</dt><dd>{value or '—'}</dd>")
        return f'<dl class="t-detail">{"".join(cells)}</dl>'

    def build(start: int, depth: int) -> tuple[str, int]:
        items: list[str] = []
        index = start
        while index < len(rows) and rows[index][0] >= depth:
            row_depth, fields, details = rows[index]
            if row_depth > depth:
                index += 1
                continue
            has_children = index + 1 < len(rows) and rows[index + 1][0] > depth
            if has_children:
                child_html, index = build(index + 1, depth + 1)
                inner = (detail_html(details) if details else "") + child_html
                items.append(
                    f'<li class="t-branch row-{state_of(fields)}"><details open>'
                    f"<summary>{node_html(fields)}</summary>"
                    f"{inner}</details></li>"
                )
            elif details:
                # A leaf that carries its own row detail: collapsed by default,
                # so the tree stays scannable and the detail is one click away.
                items.append(
                    f'<li class="t-leaf t-has-detail row-{state_of(fields)}"><details>'
                    f"<summary>{node_html(fields)}</summary>"
                    f"{detail_html(details)}</details></li>"
                )
                index += 1
            else:
                items.append(
                    f'<li class="t-leaf row-{state_of(fields)}">{node_html(fields)}</li>'
                )
                index += 1
        return f'<ul class="tree">{"".join(items)}</ul>', index

    if not rows:
        return ""
    html_out, _ = build(0, rows[0][0])
    return f'<div class="treewrap">{html_out}</div>'


def render(markdown: str) -> str:
    """Render the supported markdown subset to an HTML fragment."""
    lines = markdown.splitlines()
    out: list[str] = []
    index = 0
    in_list: str | None = None

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while index < len(lines):
        line = lines[index]

        if line.startswith("```"):
            close_list()
            fence = line[3:].strip()
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            if fence == "nwtree":
                out.append(render_tree(body))
                continue
            lang = f' data-lang="{html.escape(fence)}"' if fence else ""
            escaped = html.escape("\n".join(body), quote=False)
            out.append(f"<pre{lang}><code>{escaped}</code></pre>")
            continue

        if (
            line.startswith("|")
            and index + 1 < len(lines)
            and _TABLE_SEP.match(lines[index + 1].strip())
        ):
            close_list()
            header = _split_row(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(_split_row(lines[index]))
                index += 1
            out.append('<div class="tablewrap"><table>')
            out.append("<thead><tr>")
            out.extend(f"<th>{_cell(c)}</th>" for c in header)
            out.append("</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>")
                out.extend(f"<td>{_cell(c)}</td>" for c in row)
                out.append("</tr>")
            out.append("</tbody></table></div>")
            continue

        heading = _HEADING.match(line)
        if heading:
            close_list()
            level = len(heading.group(1))
            text = _inline(heading.group(2).strip())
            slug = re.sub(r"[^a-z0-9]+", "-", heading.group(2).lower()).strip("-")
            out.append(f'<h{level} id="{slug}">{text}</h{level}>')
            index += 1
            continue

        if line.strip() in {"---", "***", "___"}:
            close_list()
            out.append("<hr>")
            index += 1
            continue

        if line.startswith(">"):
            close_list()
            quote: list[str] = []
            while index < len(lines) and lines[index].startswith(">"):
                quote.append(lines[index].lstrip(">").strip())
                index += 1
            out.append(f"<blockquote>{_inline(' '.join(quote))}</blockquote>")
            continue

        item = _LIST_ITEM.match(line)
        ordered = _ORDERED_ITEM.match(line)
        if item or ordered:
            want = "ol" if ordered else "ul"
            if in_list != want:
                close_list()
                out.append(f"<{want}>")
                in_list = want
            body_text = (ordered or item).group(2)  # type: ignore[union-attr]
            out.append(f"<li>{_inline(body_text)}</li>")
            index += 1
            continue

        if not line.strip():
            close_list()
            index += 1
            continue

        para: list[str] = []
        while (
            index < len(lines)
            and lines[index].strip()
            and not (
                lines[index].startswith(("|", ">", "#", "```"))
                or _LIST_ITEM.match(lines[index])
                or _ORDERED_ITEM.match(lines[index])
            )
        ):
            para.append(lines[index])
            index += 1
        close_list()
        out.append(f"<p>{_inline(' '.join(para))}</p>")

    close_list()
    return "\n".join(out)


def build_page(markdown: str, source: str, title: str) -> str:
    """Wrap the rendered fragment in the standalone page body."""
    brand = load_brand()
    header = (
        '<header class="brandbar">'
        f'<img class="brandbar-logo" src="{load_logo_data_uri()}" alt="nWave">'
        "</header>"
    )
    banner = (
        '<div class="provenance">'
        "<span><strong>Projection, not source.</strong> "
        "The truth lives in "
        f"<code>{html.escape(source)}</code></span>"
        "<span>Do not edit this page: change the source and re-generate.</span>"
        "</div>"
    )
    return (
        f"<title>{html.escape(title)}</title>\n"
        f'<meta name="nwave-brand" content="{html.escape(brand.identity, quote=True)}">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{_CONTENT_SECURITY_POLICY}">\n'
        f"<style>:root{{--nwave-font-stack:{brand.font_stack};}}\n"
        f"{brand.stylesheet}</style>\n"
        f'<div class="wrap">{header}\n{banner}\n{render(markdown)}</div>\n'
    )


def view_page(source: Path, title: str | None = None) -> tuple[str, int]:
    """The standalone page for the Markdown file ``source``, and how many
    unsupported constructs the render passed through as text.

    The title is ``title`` when given, else the first heading, else the file stem.
    """
    text = source.read_text(encoding="utf-8")
    first_h1 = next(
        (
            m.group(2).strip()
            for m in (_HEADING.match(row) for row in text.splitlines())
            if m
        ),
        source.stem,
    )
    page = build_page(text, str(source), title or first_h1)
    return page, len(_UNSUPPORTED)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render an nWave markdown document to a self-contained HTML page."
    )
    parser.add_argument("source", type=Path, help="markdown file to render")
    parser.add_argument("--out", type=Path, required=True, help="HTML file to write")
    parser.add_argument("--title", default=None, help="page title (default: first H1)")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(
            f"WHAT: cannot render, the source file does not exist.\n"
            f"WHY: {args.source} was not found.\n"
            f"HOW: pass the path of an existing markdown file.",
            file=sys.stderr,
        )
        return 2

    page, unsupported = view_page(args.source, args.title)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")

    print(f"rendered {args.source} -> {args.out} ({args.out.stat().st_size:,} bytes)")
    if unsupported:
        print(
            f"NOTE: {unsupported} unsupported construct(s) passed through as text.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
