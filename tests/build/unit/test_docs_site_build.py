"""Unit tests for `scripts/docs_site/build_site.py` pure logic.

Guards the highest-risk pure functions of the documentation-site generator:
slug mapping, link rewriting (the part most likely to silently break), title
extraction, and Divio quadrant classification. No git, no pandoc, no I/O.

Lean test budget: behavior-first, one test per non-overlapping behavior.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module():
    repo_root = Path(__file__).resolve().parents[3]
    target = repo_root / "scripts" / "docs_site" / "build_site.py"
    spec = importlib.util.spec_from_file_location("docs_site_build_site", target)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bs():
    return _load_module()


# ---------------------------------------------------------------------------
# doc_url — path → site slug
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,expected",
    [
        ("docs/guides/tutorial-x/README.md", "guides/tutorial-x"),
        ("docs/guides/enforcement-recipes.md", "guides/enforcement-recipes"),
        ("docs/reference/index.md", "reference"),
        ("docs/reference/agents/index.md", "reference/agents"),
        ("docs/reference/agents/nw-x.md", "reference/agents/nw-x"),
    ],
)
def test_doc_url_maps_paths_to_slugs(bs, path, expected) -> None:
    assert bs.doc_url(path) == expected


# ---------------------------------------------------------------------------
# rewrite_links — relative hrefs/srcs → absolute site / GitHub URLs
# ---------------------------------------------------------------------------


def _rewrite(bs, html: str, source: str, version: str = "v1.0.0") -> str:
    return bs.rewrite_links(html, source, version, set())


def test_rewrite_intra_doc_md_link_to_site_url(bs) -> None:
    src = "docs/guides/HOW-TO.md"
    out = _rewrite(bs, '<a href="./installation-guide/README.md">x</a>', src)
    assert 'href="/v1.0.0/guides/installation-guide/"' in out


def test_rewrite_sibling_md_link(bs) -> None:
    src = "docs/reference/agents/nw-a.md"
    out = _rewrite(bs, '<a href="nw-b.md">b</a>', src)
    assert 'href="/v1.0.0/reference/agents/nw-b/"' in out


def test_rewrite_outside_root_link_to_github(bs) -> None:
    src = "docs/reference/agents/nw-a.md"
    out = _rewrite(bs, '<a href="../../../nWave/skills/s/SKILL.md">s</a>', src)
    assert (
        'href="https://github.com/nWave-ai/nWave/blob/v1.0.0/nWave/skills/s/SKILL.md"'
        in out
    )


def test_rewrite_asset_src_preserves_under_version(bs) -> None:
    src = "docs/guides/tutorial-x/README.md"
    out = _rewrite(bs, '<img src="diagram.png">', src)
    assert 'src="/v1.0.0/guides/tutorial-x/diagram.png"' in out


def test_rewrite_preserves_anchor_on_md_link(bs) -> None:
    src = "docs/guides/a.md"
    out = _rewrite(bs, '<a href="b.md#section">b</a>', src)
    assert 'href="/v1.0.0/guides/b/#section"' in out


@pytest.mark.parametrize(
    "href",
    [
        "https://example.com",
        "#local-anchor",
        "mailto:x@y.z",
        "/already/absolute",
    ],
)
def test_rewrite_leaves_external_and_absolute_untouched(bs, href) -> None:
    out = _rewrite(bs, f'<a href="{href}">x</a>', "docs/guides/a.md")
    assert f'href="{href}"' in out


# ---------------------------------------------------------------------------
# extract_title
# ---------------------------------------------------------------------------


def test_extract_title_prefers_front_matter(bs) -> None:
    md = '---\ntitle: "Real Title"\n---\n# Heading\n'
    assert bs.extract_title(md, "slug") == "Real Title"


def test_extract_title_falls_back_to_first_h1(bs) -> None:
    assert bs.extract_title("# My Heading\n\nbody", "slug") == "My Heading"


def test_extract_title_falls_back_to_slug(bs) -> None:
    assert bs.extract_title("no heading here", "my-slug") == "My Slug"


# ---------------------------------------------------------------------------
# build_nav — Divio classification + drift bucketing
# ---------------------------------------------------------------------------


def test_build_head_extra_latest_is_indexable(bs) -> None:
    out = bs.build_head_extra(canonical_url="/latest/guides/a/", indexable=True)
    assert 'rel="canonical"' in out
    assert "/latest/guides/a/" in out
    assert "noindex" not in out


def test_build_head_extra_versioned_is_noindex(bs) -> None:
    out = bs.build_head_extra(canonical_url="/latest/guides/a/", indexable=False)
    assert "noindex,follow" in out


def test_edit_links_versioned_has_main_and_tag(bs) -> None:
    out = bs.edit_links("docs/guides/a.md", "v3.1.0")
    assert "/blob/main/docs/guides/a.md" in out
    assert "/blob/v3.1.0/docs/guides/a.md" in out


def test_edit_links_latest_has_only_main(bs) -> None:
    out = bs.edit_links("docs/guides/a.md", "latest")
    assert "/blob/main/docs/guides/a.md" in out
    assert "/blob/latest/" not in out


def _pager_nav():
    return [
        {
            "title": "Tutorials",
            "section": "tutorials",
            "children": [
                {"title": "A", "url": "/{V}/guides/a/", "children": []},
                {"title": "B", "url": "/{V}/guides/b/", "children": []},
                {"title": "C", "url": "/{V}/guides/c/", "children": []},
            ],
        }
    ]


def test_build_pager_prev_next(bs) -> None:
    out = bs.build_pager(_pager_nav(), "tutorials", "/v1/guides/b/", "v1")
    assert "/v1/guides/a/" in out  # prev
    assert "/v1/guides/c/" in out  # next
    assert "Previous" in out and "Next" in out


def test_build_pager_first_has_no_prev(bs) -> None:
    out = bs.build_pager(_pager_nav(), "tutorials", "/v1/guides/a/", "v1")
    assert "Next" in out
    assert "Previous" not in out


def test_build_pager_landing_returns_empty(bs) -> None:
    assert bs.build_pager(_pager_nav(), None, "/v1/", "v1") == ""


def test_active_section_for_matches_page(bs) -> None:
    assert bs.active_section_for(_pager_nav(), "/v1/guides/b/") == "tutorials"
    assert bs.active_section_for(_pager_nav(), "/v1/") is None


def test_build_nav_classifies_and_buckets_unmatched(bs) -> None:
    config = {
        "sections": [
            {"id": "tut", "title": "Tutorials", "paths": ["docs/guides/tutorial-"]},
            {"id": "ref", "title": "Reference", "paths": ["docs/reference"]},
        ]
    }
    paths = [
        "docs/guides/tutorial-x/README.md",
        "docs/reference/agents/nw-a.md",
        "docs/guides/orphan.md",  # matches no section -> "More"
    ]
    titles = {p: p for p in paths}
    nav = bs.build_nav(config, paths, titles)
    by_title = {s["title"]: s for s in nav}
    assert set(by_title) == {"Tutorials", "Reference", "More"}
    # Reference keeps its sub-grouping ("agents" branch).
    ref_titles = {c["title"] for c in by_title["Reference"]["children"]}
    assert "agents" in {t.lower() for t in ref_titles}


def test_build_nav_orders_leaves_by_siteyaml_then_alpha(bs) -> None:
    # site.yaml's curated path order is authoritative for leaf ordering;
    # pages sharing one directory prefix fall back to alphabetical. This guards
    # the what's-new ordering regression (newest-first 3.19, 3.14, 3.5 — which
    # alphabetical-by-slug would mis-sort to 3.14, 3.19, 3.5).
    config = {
        "sections": [
            {
                "id": "explanation",
                "title": "Explanation",
                "paths": [
                    "docs/guides/whats-new-v319",
                    "docs/guides/whats-new-v314",
                    "docs/guides/whats-new-v35",
                    "docs/reference",  # shared prefix -> alpha within
                ],
            }
        ]
    }
    # Input arrives alphabetical — the order that previously mis-sorted.
    paths = [
        "docs/guides/whats-new-v314/README.md",
        "docs/guides/whats-new-v319/README.md",
        "docs/guides/whats-new-v35/README.md",
        "docs/reference/b.md",
        "docs/reference/a.md",
    ]
    titles = {p: p for p in paths}
    nav = bs.build_nav(config, paths, titles)
    urls = [c["url"] for c in nav[0]["children"]]
    assert urls == [
        "/{V}/guides/whats-new-v319/",
        "/{V}/guides/whats-new-v314/",
        "/{V}/guides/whats-new-v35/",
        "/{V}/reference/a/",
        "/{V}/reference/b/",
    ]
