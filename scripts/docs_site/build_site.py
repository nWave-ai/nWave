#!/usr/bin/env python3
"""Build the versioned nWave documentation site under ``_site/``.

The generator is **corpus-agnostic** and **stateless**: it reads the entire
repository (git tags + the doc roots) and regenerates the whole site from
scratch every run, so the output never drifts from repository state. Delete a
tag and it vanishes from the version selector on the next build.

For every git tag matching ``vN.N.N`` it extracts the markdown under the doc
roots (``docs/guides/`` and ``docs/reference/``), renders each file to HTML via
pandoc, and writes ``_site/{tag}/{slug}/index.html``. It also emits:

- ``_site/versions.json`` — manifest of every version with its date and a
  hierarchical navigation tree. Drives the client-side version combobox and the
  sidebar in ``static/site.js``.
- ``_site/index.html`` — landing page (Divio quadrant cards) for the newest
  version.
- ``_site/{tag}/index.html`` — per-version landing page.
- ``_site/{tag}/{section}/index.html`` — section/quadrant index pages.
- ``_site/static/`` — mirror of ``scripts/docs_site/static/``.

Modes:

- default (tags): iterate every ``vN.N.N`` tag. Used by CI in the public repo.
- ``--working-tree``: also include the current working tree as a synthetic
  ``dev`` version. Used for local preview without needing doc-bearing tags.
- ``--working-tree-only``: ONLY build the working tree as ``dev`` (fast local
  iteration).

Environment variables:

- ``BUILD_SITE_DIR`` — override the output directory (default ``_site``).

Requires: pandoc on PATH; a git working tree with the relevant tags present.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SELF_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SELF_DIR / "templates"
STATIC_DIR = SELF_DIR / "static"
CONFIG_PATH = SELF_DIR / "site.yaml"
SITE_DIR = REPO_ROOT / os.environ.get("BUILD_SITE_DIR", "_site")

# Content source repository: the git tree whose tags + docs are rendered. This
# is decoupled from where the generator itself lives (SELF_DIR / REPO_ROOT) and
# from the output (SITE_DIR). It defaults to this repo for local preview; in CI
# it points at a checkout of the PUBLIC repo, so the published site is built
# from public tags only and the generator never has to live in the public repo.
# Override with DOCS_SOURCE_REPO or --source; resolved definitively in main().
SOURCE_REPO = Path(os.environ.get("DOCS_SOURCE_REPO", REPO_ROOT)).resolve()

# Doc roots, relative to repo root. Everything under these is rendered.
DOC_ROOTS = ("docs/guides", "docs/reference")

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

# Public GitHub repo, for rewriting links that point outside the doc roots
# (e.g. into nWave/skills/**/SKILL.md) to a browsable source location.
GITHUB_REPO = "https://github.com/nWave-ai/nWave"


# ---------- git helpers ----------


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=SOURCE_REPO, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(
            f"error: git {' '.join(args)} failed\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(result.returncode)
    return result.stdout.strip()


def _semver_key(tag: str) -> tuple[int, int, int]:
    m = TAG_PATTERN.match(tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


def list_tags() -> list[str]:
    raw = run_git(["tag", "--list", "v*"])
    tags = [t for t in raw.splitlines() if TAG_PATTERN.match(t)]
    tags.sort(key=_semver_key)
    return tags


def tag_date(tag: str) -> str:
    return run_git(["log", "-1", "--format=%ad", "--date=short", tag])


def files_at_tag(tag: str) -> list[str]:
    """Repo-relative paths of every ``.md`` under the doc roots at ``tag``."""
    raw = run_git(["ls-tree", "-r", "--name-only", tag, "--", *DOC_ROOTS])
    return sorted(p for p in raw.splitlines() if p.endswith(".md"))


def assets_at_tag(tag: str) -> list[str]:
    """Repo-relative paths of every non-``.md`` file under the doc roots."""
    raw = run_git(["ls-tree", "-r", "--name-only", tag, "--", *DOC_ROOTS])
    return sorted(p for p in raw.splitlines() if not p.endswith(".md"))


def content_at_tag(tag: str, path: str) -> str:
    return run_git(["show", f"{tag}:{path}"])


# ---------- working-tree source (mirror of the git helpers) ----------


def files_in_worktree() -> list[str]:
    out: list[str] = []
    for root in DOC_ROOTS:
        base = SOURCE_REPO / root
        if base.is_dir():
            out += [str(p.relative_to(SOURCE_REPO)) for p in base.rglob("*.md")]
    return sorted(out)


def assets_in_worktree() -> list[str]:
    out: list[str] = []
    for root in DOC_ROOTS:
        base = SOURCE_REPO / root
        if base.is_dir():
            out += [
                str(p.relative_to(SOURCE_REPO))
                for p in base.rglob("*")
                if p.is_file() and p.suffix != ".md"
            ]
    return sorted(out)


# ---------- content helpers ----------


def doc_url(path: str) -> str:
    """Map a repo-relative doc path to its site slug.

    ``docs/guides/tutorial-x/README.md`` -> ``guides/tutorial-x``
    ``docs/guides/enforcement-recipes.md`` -> ``guides/enforcement-recipes``
    ``docs/reference/agents/index.md`` -> ``reference/agents``
    ``docs/reference/agents/nw-x.md`` -> ``reference/agents/nw-x``
    """
    rel = path
    if rel.startswith("docs/"):
        rel = rel[len("docs/") :]
    rel = re.sub(r"\.md$", "", rel)
    rel = re.sub(r"/(README|index)$", "", rel)
    if rel in ("README", "index"):
        rel = ""
    return rel


def asset_url(path: str) -> str:
    """Map a repo-relative asset path to its site path (``docs/`` stripped)."""
    return path[len("docs/") :] if path.startswith("docs/") else path


def extract_title(markdown: str, fallback: str) -> str:
    if markdown.startswith("---\n"):
        end = markdown.find("\n---\n", 4)
        if end > 0:
            m = re.search(r"^title:\s*(.+)$", markdown[4:end], re.MULTILINE)
            if m:
                return m.group(1).strip().strip("\"'")
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").title()


def strip_front_matter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    end = markdown.find("\n---\n", 4)
    return markdown if end < 0 else markdown[end + len("\n---\n") :]


def strip_leading_h1(markdown: str) -> str:
    lines = markdown.splitlines(keepends=True)
    out: list[str] = []
    saw = False
    for line in lines:
        if not saw and line.startswith("# "):
            saw = True
            continue
        if saw and not out and line.strip() == "":
            continue
        out.append(line)
    return "".join(out) if saw else markdown


# ---------- pandoc ----------


def render_markdown(content: str) -> str:
    """Render a markdown body to an HTML fragment (no standalone wrapper)."""
    cmd = [
        "pandoc",
        "--from=gfm",
        "--to=html5",
        "--section-divs",
        "--wrap=preserve",
        "--no-highlight",
    ]
    result = subprocess.run(cmd, input=content, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"error: pandoc failed\n{result.stderr}", file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout


# ---------- link rewriting ----------

_HREF_RE = re.compile(r'(href|src)="([^"]*)"')


def rewrite_links(
    body_html: str, source_path: str, version: str, doc_paths: set[str]
) -> str:
    """Rewrite relative hrefs/srcs in rendered HTML to absolute site paths.

    - ``.md`` targets inside a doc root -> ``/{version}/{slug}/``
    - non-``.md`` targets inside a doc root (assets) -> ``/{version}/{path}``
    - targets outside the doc roots -> GitHub blob URL at this version
    - external URLs, anchors, mailto -> left untouched
    """
    source_dir = str(Path(source_path).parent)

    def repl(m: re.Match[str]) -> str:
        attr, url = m.group(1), m.group(2)
        if (
            not url
            or url.startswith("#")
            or "://" in url
            or url.startswith("mailto:")
            or url.startswith("/")
            or url.startswith("data:")
        ):
            return m.group(0)
        anchor = ""
        if "#" in url:
            url, anchor = url.split("#", 1)
            anchor = "#" + anchor
        if not url:  # was a bare anchor after split
            return f'{attr}="{anchor}"'
        # Resolve the relative reference against the source file's directory.
        target = os.path.normpath(os.path.join(source_dir, url))
        in_roots = any(target == r or target.startswith(r + "/") for r in DOC_ROOTS)
        if in_roots and target.endswith(".md"):
            slug = doc_url(target)
            new = f"/{version}/{slug}/" if slug else f"/{version}/"
        elif in_roots:
            new = f"/{version}/{asset_url(target)}"
        else:
            # Outside the doc roots — link to browsable source on GitHub.
            new = f"{GITHUB_REPO}/blob/{version}/{target}"
        return f'{attr}="{new}{anchor}"'

    return _HREF_RE.sub(repl, body_html)


# ---------- navigation tree ----------


def build_nav(config: dict, doc_paths: list[str], titles: dict[str, str]) -> list[dict]:
    """Build the hierarchical sidebar nav grouped by Divio section.

    ``site.yaml`` defines ordered top-level sections, each with one or more
    path prefixes. Pages are assigned to the first section whose prefix matches;
    unmatched pages go to a trailing "More" section (logged as drift).
    """
    sections = config.get("sections", [])
    # url -> (slug, title, depth-sortable path)
    assigned: dict[str, list[str]] = {sec["title"]: [] for sec in sections}
    more: list[str] = []

    for path in doc_paths:
        placed = False
        for sec in sections:
            for prefix in sec.get("paths", []):
                if path == prefix or path.startswith(prefix):
                    assigned[sec["title"]].append(path)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            more.append(path)

    if more:
        print(
            f"  note: {len(more)} page(s) unclassified, bucketed under 'More': "
            + ", ".join(doc_url(p) for p in more[:8])
            + (" ..." if len(more) > 8 else ""),
            file=sys.stderr,
        )

    def tree_for(paths: list[str]) -> list[dict]:
        """Build a nested tree from a flat list of doc paths.

        ``doc_url`` has already collapsed ``index``/``README`` onto their
        directory, so each path maps to exactly one node. The leading doc-root
        segment (``guides``/``reference``) is stripped for grouping — the
        section title already conveys it — while meaningful sub-grouping
        (e.g. ``reference/agents/*``) is preserved. A page whose slug is just
        the root (e.g. ``reference``) becomes a leading "Overview" leaf.

        ``paths`` must already be in the desired display order (the caller
        orders them by their position in the section's ``site.yaml`` prefix
        list); insertion order is preserved into the rendered tree.
        """
        root: dict = {"children": {}, "page": None}
        for path in paths:
            slug = doc_url(path)
            page = {"slug": slug, "title": titles.get(path, slug)}
            rel = slug.split("/", 1)[1] if "/" in slug else ""
            relparts = rel.split("/") if rel else []
            node = root
            for part in relparts:
                node = node["children"].setdefault(part, {"children": {}, "page": None})
            node["page"] = page
        out: list[dict] = []
        if root["page"]:
            out.append(
                {
                    "title": "Overview",
                    "url": f"/{{V}}/{root['page']['slug']}/",
                    "children": [],
                }
            )
        out.extend(_flatten(root))
        return out

    def _flatten(node: dict) -> list[dict]:
        out: list[dict] = []
        for name, child in node["children"].items():
            page = child["page"]
            out.append(
                {
                    "title": page["title"] if page else name.replace("-", " ").title(),
                    "url": f"/{{V}}/{page['slug']}/" if page else None,
                    "children": _flatten(child),
                }
            )
        return out

    def _leaf_order(sec_paths: list[str]):
        """Sort key: index of the first matching site.yaml prefix, then path.

        Leaves render in the curated ``site.yaml`` order; pages sharing one
        directory prefix (e.g. all of ``docs/reference``) fall back to
        alphabetical within that prefix.
        """

        def key(path: str) -> tuple[int, str]:
            for i, prefix in enumerate(sec_paths):
                if path == prefix or path.startswith(prefix):
                    return (i, path)
            return (len(sec_paths), path)

        return key

    nav: list[dict] = []
    for sec in sections:
        paths = assigned[sec["title"]]
        if not paths:
            continue
        paths = sorted(paths, key=_leaf_order(sec.get("paths", [])))
        nav.append(
            {
                "title": sec["title"],
                "url": None,
                "section": sec.get("id", sec["title"].lower()),
                "children": tree_for(paths),
            }
        )
    if more:
        nav.append(
            {
                "title": "More",
                "url": None,
                "section": "more",
                "children": tree_for(sorted(more)),
            }
        )
    return nav


# ---------- page assembly ----------


def load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def render_page(
    template: str,
    *,
    title: str,
    version: str,
    current_url: str,
    body: str,
    config: dict,
    category_nav: str = "",
    head_extra: str = "",
) -> str:
    return (
        template.replace("{{TITLE}}", html.escape(title))
        .replace("{{VERSION}}", html.escape(version))
        .replace("{{CURRENT_URL}}", html.escape(current_url))
        .replace("{{SITE_NAME}}", html.escape(config.get("site_name", "nWave Docs")))
        .replace("{{CATEGORY_NAV}}", category_nav)
        .replace("{{HEAD_EXTRA}}", head_extra)
        .replace("{{BODY}}", body)
    )


# Canonical host for absolute URLs in <link rel=canonical> and the sitemap.
SITE_ORIGIN = "https://docs.nwave.ai"


def build_head_extra(*, canonical_url: str, indexable: bool) -> str:
    """SEO <head> tags: a canonical link plus noindex on non-latest pages.

    Only the ``/latest/`` tree is indexable; every versioned tree carries
    ``noindex`` and canonicalises to its ``/latest/`` equivalent, so search
    engines index one copy of the docs instead of one per release.
    """
    lines = [f'  <link rel="canonical" href="{SITE_ORIGIN}{canonical_url}">']
    if not indexable:
        lines.append('  <meta name="robots" content="noindex,follow">')
    return "\n".join(lines)


def edit_links(path: str, version: str) -> str:
    """'Edit this page' / 'View source' GitHub links for a doc page.

    The editable source lives on ``main``; a versioned page also offers a
    read-only link to its source at that tag.
    """
    main_url = f"{GITHUB_REPO}/blob/main/{path}"
    parts = [
        f'<a href="{main_url}" target="_blank" rel="noopener">Edit this page on GitHub</a>'
    ]
    if version not in ("latest", "dev"):
        tag_url = f"{GITHUB_REPO}/blob/{version}/{path}"
        parts.append(
            f'<a href="{tag_url}" target="_blank" rel="noopener">View source at {html.escape(version)}</a>'
        )
    return '<div class="doc-edit">' + " · ".join(parts) + "</div>"


def ordered_section_pages(section: dict, version: str) -> list[dict]:
    """Depth-first ordered [{url,title}] for a nav section (for prev/next)."""
    out: list[dict] = []

    def walk(nodes: list[dict]) -> None:
        for n in nodes:
            if n.get("url"):
                out.append(
                    {"url": n["url"].replace("{V}", version), "title": n["title"]}
                )
            walk(n.get("children", []))

    walk(section.get("children", []))
    return out


def build_pager(
    nav: list[dict], active_section: str | None, current_url: str, version: str
) -> str:
    """Prev/next links within the current category."""
    if not active_section:
        return ""
    section = next((s for s in nav if s.get("section") == active_section), None)
    if not section:
        return ""
    pages = ordered_section_pages(section, version)
    idx = next((i for i, p in enumerate(pages) if p["url"] == current_url), None)
    if idx is None:
        return ""
    prev_p = pages[idx - 1] if idx > 0 else None
    next_p = pages[idx + 1] if idx < len(pages) - 1 else None
    if not prev_p and not next_p:
        return ""
    left = (
        f'<a class="doc-pager__link doc-pager__prev" href="{html.escape(prev_p["url"])}">'
        f'<span class="doc-pager__dir">← Previous</span>'
        f'<span class="doc-pager__title">{html.escape(prev_p["title"])}</span></a>'
        if prev_p
        else "<span></span>"
    )
    right = (
        f'<a class="doc-pager__link doc-pager__next" href="{html.escape(next_p["url"])}">'
        f'<span class="doc-pager__dir">Next →</span>'
        f'<span class="doc-pager__title">{html.escape(next_p["title"])}</span></a>'
        if next_p
        else "<span></span>"
    )
    return (
        f'<nav class="doc-pager" aria-label="Category pagination">{left}{right}</nav>'
    )


def quadrant_target(q: dict, nav: list[dict], version: str) -> str:
    """Resolve a quadrant's link at ``version`` with graceful degradation.

    Prefer the configured ``landing`` slug; if it does not exist at this
    version, fall back to the quadrant's first existing page, then the version
    root — so a category link is never dead across the version history.
    """
    valid = _all_urls(nav, version)
    configured = f"/{version}/{q['landing'].lstrip('/')}" if q.get("landing") else None
    if configured and configured in valid:
        return configured
    return _section_first_url(nav, q.get("section", ""), version) or f"/{version}/"


def category_links(config: dict, nav: list[dict], version: str) -> list[dict]:
    """The ordered top-nav categories (Divio quadrants) for ``version``."""
    out: list[dict] = []
    for q in config.get("quadrants", []):
        out.append(
            {
                "title": q["title"],
                "section": q.get("section", ""),
                "url": quadrant_target(q, nav, version),
            }
        )
    return out


def active_section_for(nav: list[dict], current_url: str) -> str | None:
    """The nav section id whose pages contain ``current_url`` (or None)."""
    for sec in nav:
        if current_url in _all_urls(sec.get("children", []), _url_version(current_url)):
            return sec.get("section")
    return None


def _url_version(url: str) -> str:
    """Extract the version segment from a ``/{version}/...`` site URL."""
    parts = url.strip("/").split("/", 1)
    return parts[0] if parts else ""


def render_category_nav(cats: list[dict], active_section: str | None) -> str:
    """Build the header category-link HTML, marking the active quadrant."""
    items = []
    for c in cats:
        cls = "nw-navbar-link"
        if c["section"] == active_section:
            cls += " active"
        items.append(
            f'      <a class="{cls}" href="{html.escape(c["url"])}">'
            f"{html.escape(c['title'])}</a>"
        )
    return "\n".join(items)


def build_version(
    version: str,
    date: str,
    config: dict,
    *,
    source_tag: str | None,
    landing_html: str = "",
    latest_slugs: set[str] | None = None,
) -> dict:
    """Render every doc at ``version``; return its versions.json entry.

    ``source_tag`` is the git ref to read content from, or None for the
    working tree. ``landing_html`` is the pre-rendered getting-started prose
    (with ``{{V}}`` version placeholders) shown on the version landing page.
    ``latest_slugs`` is the set of slugs that exist in the ``latest`` tree,
    used to canonicalise versioned pages to their ``/latest/`` equivalent.
    """
    latest_slugs = latest_slugs or set()
    indexable = version == "latest"
    print(f"build_site: {version}", file=sys.stderr)
    if source_tag is not None:
        doc_paths = files_at_tag(source_tag)
        asset_paths = assets_at_tag(source_tag)

        def read(p: str) -> str:
            return content_at_tag(source_tag, p)
    else:
        doc_paths = files_in_worktree()
        asset_paths = assets_in_worktree()

        def read(p: str) -> str:
            return (SOURCE_REPO / p).read_text(encoding="utf-8")

    doc_path_set = set(doc_paths)
    titles: dict[str, str] = {}
    raw_by_path: dict[str, str] = {}
    for path in doc_paths:
        raw = read(path)
        raw_by_path[path] = raw
        titles[path] = extract_title(raw, Path(path).stem)

    page_template = load_template("page.html")

    # Navigation is needed before rendering pages: each page's header carries
    # the Divio category links, with the category containing the page marked
    # active.
    nav = build_nav(config, doc_paths, titles)
    cats = category_links(config, nav, version)

    for path in doc_paths:
        raw = raw_by_path[path]
        slug = doc_url(path)
        title = titles[path]
        body_md = strip_leading_h1(strip_front_matter(raw))
        body_html = render_markdown(body_md)
        body_html = rewrite_links(body_html, path, version, doc_path_set)
        current_url = f"/{version}/{slug}/" if slug else f"/{version}/"
        active = active_section_for(nav, current_url)
        # Canonicalise versioned pages onto their /latest/ equivalent when it
        # exists; the latest tree canonicalises to itself.
        if version != "latest" and slug in latest_slugs:
            canonical = f"/latest/{slug}/" if slug else "/latest/"
        else:
            canonical = current_url
        # Only the latest tree is search-indexed (data-pagefind-body marker)
        # and crawler-indexable.
        body_attr = " data-pagefind-body" if indexable else ""
        page_body = (
            f'<article class="doc"{body_attr}>\n'
            f'  <h1 class="doc__title">{html.escape(title)}</h1>\n'
            f"{body_html}\n"
            f"  {edit_links(path, version)}\n"
            f"  {build_pager(nav, active, current_url, version)}\n"
            f"</article>"
        )
        page = render_page(
            page_template,
            title=title,
            version=version,
            current_url=current_url,
            body=page_body,
            config=config,
            category_nav=render_category_nav(cats, active),
            head_extra=build_head_extra(canonical_url=canonical, indexable=indexable),
        )
        out_dir = SITE_DIR / version / slug if slug else SITE_DIR / version
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(page, encoding="utf-8")

    # Mirror assets (images, etc.) preserving their docs-relative path.
    for path in asset_paths:
        dst = SITE_DIR / version / asset_url(path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if source_tag is not None:
            blob = subprocess.run(
                ["git", "show", f"{source_tag}:{path}"],
                cwd=SOURCE_REPO,
                capture_output=True,
            )
            if blob.returncode == 0:
                dst.write_bytes(blob.stdout)
        else:
            shutil.copyfile(SOURCE_REPO / path, dst)

    # Per-version landing page (getting-started prose + Divio quadrant cards).
    write_version_landing(version, date, config, nav, page_template, cats, landing_html)

    return {
        "version": version,
        "date": date,
        "nav": nav,
    }


# ---------- landing + index pages ----------


def _all_urls(nav: list[dict], version: str) -> set[str]:
    """Every page URL reachable in this version's nav (for existence checks)."""
    out: set[str] = set()

    def walk(nodes: list[dict]) -> None:
        for n in nodes:
            if n.get("url"):
                out.add(n["url"].replace("{V}", version))
            walk(n.get("children", []))

    walk(nav)
    return out


def _section_first_url(nav: list[dict], section_id: str, version: str) -> str | None:
    """First page URL within the nav section whose id matches ``section_id``."""
    for sec in nav:
        if sec.get("section") == section_id:
            urls = _all_urls(sec.get("children", []), version)
            return sorted(urls)[0] if urls else None
    return None


def _video_html(config: dict) -> str:
    """Optional hero video. Renders only when ``landing.video_embed`` is set,
    so the slot is reserved for the future without showing an empty box now."""
    embed = (config.get("landing", {}) or {}).get("video_embed", "")
    if not embed:
        return ""
    return f"""  <div class="landing__video">
    <div class="landing__video-frame">
      <iframe src="{html.escape(embed)}" title="What is nWave?"
        loading="lazy" allowfullscreen
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>
    </div>
  </div>"""


def write_version_landing(
    version: str,
    date: str,
    config: dict,
    nav: list[dict],
    template: str,
    cats: list[dict],
    landing_html: str = "",
) -> None:
    """Per-version landing: hero, optional video, getting-started prose, and
    the four Divio quadrant cards.

    Card targets degrade gracefully: if the configured landing slug does not
    exist at this version (e.g. an index added in a later release), the card
    falls back to the quadrant's first existing page, then the version root —
    so no card is ever a dead link across the version history.
    """
    quadrants = config.get("quadrants", [])
    valid = _all_urls(nav, version)
    cards = []
    for q in quadrants:
        target = (
            f"/{version}/{q['landing'].lstrip('/')}"
            if q.get("landing")
            else f"/{version}/"
        )
        if target not in valid:
            target = (
                _section_first_url(nav, q.get("section", ""), version) or f"/{version}/"
            )
        cards.append(
            f'''      <a class="nw-card quadrant-card" href="{html.escape(target)}">
        <div class="quadrant-card__kicker">{html.escape(q.get("kicker", ""))}</div>
        <h3 class="quadrant-card__title">{html.escape(q["title"])}</h3>
        <p class="quadrant-card__desc">{html.escape(q.get("description", ""))}</p>
        <span class="quadrant-card__cta">{html.escape(q.get("cta", "Explore"))} &rarr;</span>
      </a>'''
        )
    cards_html = "\n".join(cards)
    intro = config.get("landing", {})
    # Version-stamp the prose's links (authored with {{V}} placeholders).
    prose = landing_html.replace("{{V}}", version) if landing_html else ""
    prose_block = (
        f'  <section class="landing__guide doc">\n{prose}\n  </section>'
        if prose
        else ""
    )
    body = f"""<section class="landing">
  <div class="landing__hero">
    <p class="nw-section-label">{html.escape(intro.get("kicker", "DOCUMENTATION"))}</p>
    <h1 class="landing__headline">{html.escape(intro.get("headline", "nWave Documentation"))}</h1>
    <p class="landing__subhead">{html.escape(intro.get("subhead", ""))}</p>
  </div>
{_video_html(config)}
{prose_block}
  <p class="nw-section-label landing__nav-label">BROWSE THE DOCS</p>
  <div class="quadrant-grid">
{cards_html}
  </div>
</section>"""
    canonical = "/latest/" if version != "latest" else f"/{version}/"
    page = render_page(
        template,
        title="Documentation",
        version=version,
        current_url=f"/{version}/",
        body=body,
        config=config,
        category_nav=render_category_nav(cats, None),
        head_extra=build_head_extra(
            canonical_url=canonical, indexable=version == "latest"
        ),
    )
    (SITE_DIR / version).mkdir(parents=True, exist_ok=True)
    (SITE_DIR / version / "index.html").write_text(page, encoding="utf-8")


def write_versions_manifest(entries: list[dict]) -> None:
    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "versions": entries,
    }
    (SITE_DIR / "versions.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def write_root_redirect(has_latest: bool, entries: list[dict]) -> None:
    """``/index.html`` -> the canonical ``/latest/`` landing (or newest)."""
    if has_latest:
        target = "/latest/"
    elif entries:
        target = f"/{entries[-1]['version']}/"
    else:
        return
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>nWave Documentation</title>
  <meta http-equiv="refresh" content="0; url={target}">
  <link rel="canonical" href="{SITE_ORIGIN}{target}">
  <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
</head>
<body>
  <p>Redirecting to the <a href="{target}">latest documentation</a>.</p>
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(html_doc, encoding="utf-8")


def write_seo_files(has_latest: bool) -> None:
    """robots.txt, a sitemap of the indexable ``/latest/`` tree, and Netlify
    redirects (``/latest/*`` is the real tree; ``/`` -> ``/latest/``)."""
    robots = f"User-agent: *\nAllow: /\nSitemap: {SITE_ORIGIN}/sitemap.xml\n"
    (SITE_DIR / "robots.txt").write_text(robots, encoding="utf-8")

    urls: list[str] = []
    if has_latest:
        for idx in (SITE_DIR / "latest").rglob("index.html"):
            rel = idx.parent.relative_to(SITE_DIR).as_posix()
            urls.append(f"{SITE_ORIGIN}/{rel}/")
    body = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in sorted(urls))
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )
    (SITE_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    # Netlify: keep /latest as the stable shareable path (it is a real tree).
    # A bare /latest (no trailing slash) resolves to its index automatically.
    (SITE_DIR / "_redirects").write_text("/  /latest/  302\n", encoding="utf-8")


def copy_static_assets() -> None:
    target = SITE_DIR / "static"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(STATIC_DIR, target)


def run_pagefind() -> None:
    """Generate the Pagefind search index over the built site.

    Only pages marked ``data-pagefind-body`` (the ``/latest/`` tree) are
    indexed. Tries a few invocation styles so it works locally and in CI;
    if none is available the build still succeeds and the search box reports
    that the index was not generated.
    """
    candidates = [
        ["pagefind"],
        ["npx", "--yes", "pagefind"],
    ]
    last_err = ""
    for base in candidates:
        try:
            result = subprocess.run(
                [*base, "--site", str(SITE_DIR)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            print(f"build_site: pagefind index built via {base[0]}", file=sys.stderr)
            return
        last_err = result.stderr.strip().splitlines()[-1] if result.stderr else ""
    print(
        "build_site: pagefind unavailable — search index skipped "
        f"(CI installs it){': ' + last_err if last_err else ''}",
        file=sys.stderr,
    )


# ---------- entry point ----------


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def render_landing_prose() -> str:
    """Render ``landing.md`` (getting-started prose) to an HTML fragment.

    Links in the source use a ``{{V}}`` placeholder for the version segment;
    it is left intact here and stamped per version by the landing writer.
    Returns "" when the file is absent.
    """
    src = SELF_DIR / "landing.md"
    if not src.is_file():
        return ""
    return render_markdown(src.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--working-tree",
        action="store_true",
        help="also build the current working tree as a synthetic 'dev' version",
    )
    parser.add_argument(
        "--working-tree-only",
        action="store_true",
        help="build ONLY the working tree as 'dev' (fast local iteration)",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="skip generating the Pagefind search index",
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        help="path to the content source repo (tags + docs) to render from; "
        "overrides $DOCS_SOURCE_REPO. Defaults to this repo.",
    )
    args = parser.parse_args()

    if args.source:
        global SOURCE_REPO
        SOURCE_REPO = Path(args.source).resolve()
    if not (SOURCE_REPO / ".git").exists():
        print(
            f"error: source repo {SOURCE_REPO} is not a git checkout "
            "(need its tags to build versions)",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"build_site: content source = {SOURCE_REPO}", file=sys.stderr)

    if not TEMPLATES_DIR.is_dir() or not STATIC_DIR.is_dir():
        print("error: missing templates/ or static/", file=sys.stderr)
        sys.exit(1)

    config = load_config()

    # The landing's getting-started prose is version-independent (links carry a
    # {{V}} placeholder stamped per version), so render it once.
    landing_html = render_landing_prose()

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Released versions that actually carry docs (tags predating the doc roots
    # are skipped — keeps the "reads the entire repo" contract without emitting
    # empty versions).
    doc_tags = (
        [t for t in list_tags() if files_at_tag(t)]
        if not args.working_tree_only
        else []
    )
    for t in (
        t for t in list_tags() if t not in doc_tags and not args.working_tree_only
    ):
        print(f"build_site: skip {t} (no docs under roots)", file=sys.stderr)

    # The /latest/ tree is the canonical, indexable copy of the newest release
    # (or the working tree when no tags exist). Compute its slugs first so every
    # versioned page can canonicalise onto its /latest/ equivalent.
    latest_source = doc_tags[-1] if doc_tags else None
    if latest_source is not None:
        latest_slugs = {doc_url(p) for p in files_at_tag(latest_source)}
        latest_date = tag_date(latest_source)
    else:
        latest_slugs = {doc_url(p) for p in files_in_worktree()}
        latest_date = today

    entries: list[dict] = []
    for tag in doc_tags:
        entries.append(
            build_version(
                tag,
                tag_date(tag),
                config,
                source_tag=tag,
                landing_html=landing_html,
                latest_slugs=latest_slugs,
            )
        )

    if args.working_tree or args.working_tree_only:
        entries.append(
            build_version(
                "dev",
                today,
                config,
                source_tag=None,
                landing_html=landing_html,
                latest_slugs=latest_slugs,
            )
        )

    # The canonical /latest/ tree: a second render of the newest source under
    # the stable "latest" label (self-canonical, indexable, search-indexed).
    has_latest = bool(latest_slugs)
    if has_latest:
        latest_entry = build_version(
            "latest",
            latest_date,
            config,
            source_tag=latest_source,
            landing_html=landing_html,
            latest_slugs=latest_slugs,
        )
        # Record which released tag /latest/ currently points at so the version
        # picker can label it "Latest (vX.Y.Z)". None when building from the
        # working tree (no tags), where there is no underlying release.
        if latest_source:
            latest_entry["alias_of"] = latest_source
        entries.append(latest_entry)

    copy_static_assets()
    write_versions_manifest(entries)
    write_root_redirect(has_latest, entries)
    write_seo_files(has_latest)
    if not args.no_search and has_latest:
        run_pagefind()

    if not entries:
        print("build_site: no versions built", file=sys.stderr)
    else:
        print(
            f"build_site: {len(entries)} version(s) under {SITE_DIR}/",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
