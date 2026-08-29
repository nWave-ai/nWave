# nWave documentation site generator

Builds the versioned documentation site published at **docs.nwave.ai**. It is a
small, dependency-light static-site generator: pandoc for markdown → HTML, plus
a single Python script. No SSG framework.

## How it works

`build_site.py` reads the **entire repository** and regenerates the **whole
site** every run, so the output never drifts from repo state:

1. Iterate every git tag matching `vN.N.N`. Skip tags that carry no docs.
2. For each version, render every `.md` under the doc roots
   (`docs/guides/`, `docs/reference/`) to HTML via pandoc, and write
   `_site/{version}/{slug}/index.html`.
3. Rewrite links: intra-doc `.md` links → site URLs; links pointing outside the
   doc roots (e.g. `nWave/skills/**/SKILL.md`) → GitHub source URLs.
4. Group pages into the four [Divio](https://docs.divio.com/documentation-system/)
   quadrants per `site.yaml`, and emit `versions.json` (drives the client-side
   version selector + sidebar) plus per-version landing pages.

Because the build is a pure function of repo state, deleting a tag removes that
version from the selector on the next run — there is no incremental state.

A second render of the newest release is published under the stable **`/latest/`**
path: it is the only crawler-indexable, search-indexed tree. Every versioned
tree carries `noindex` and a `rel=canonical` pointing at its `/latest/`
equivalent, so search engines index one copy of the docs instead of one per
release. A `sitemap.xml` (latest pages), `robots.txt`, and a Netlify `_redirects`
(`/` → `/latest/`) are emitted too.

After rendering, [Pagefind](https://pagefind.app/) indexes the `/latest/` HTML
(only pages tagged `data-pagefind-body`) into `_site/pagefind/`, which the
header search box loads on demand. The build calls `pagefind` if it is on PATH,
else `npx --yes pagefind`; pass `--no-search` to skip it.

## Files

| File | Purpose |
|------|---------|
| `build_site.py` | The generator. |
| `site.yaml` | The one curated input: Divio quadrant grouping, hero copy, and the optional landing video (`landing.video_embed`). A doc matching no section is bucketed under "More" and logged — never dropped. |
| `landing.md` | Getting-started prose shown on every version's home page. Links use a `{{V}}` placeholder for the version segment. |
| `templates/page.html` | Page shell (header with category nav + version selector, sidebar/TOC mount points, footer). |
| `static/styles.css` | nWave dark design system (tokens from `branding/design-systems/web`). |
| `static/site.js` | Searchable version picker, active-category sidebar, scrollspy, prev/next pager wiring, Pagefind search modal. |
| `static/favicon.svg` | Site icon. |

## Navigation model

The four Divio categories (Tutorials, How-To, Reference, Explanation) live in the
**top header** as links. The **left rail** shows only the sub-tree of the
category you're currently in, so it stays focused rather than listing all four.
The **right rail** is the on-this-page outline (scrollspy). Each page ends with
an **Edit on GitHub** link and a **prev/next pager** within its category. The
landing page collapses both rails and centres on the getting-started content.

The header also carries **search** (`/` to focus; Pagefind modal) and a
**searchable version picker** — pinned Latest/dev, released versions collapsed to
the newest patch per minor line with a "show all" toggle and a live filter.

## Roadmap / planned

- **Cheat sheets** — printable HTML + downloadable PDF quick-references. These
  will plug in as an additional render target alongside the per-page HTML
  (a new output type in `build_site.py` + a print stylesheet). Not built yet.

## Local preview

```bash
pip install pyyaml          # the only non-stdlib dependency; pandoc must be on PATH

# Fast: render only the current working tree as a 'dev' version.
python scripts/docs_site/build_site.py --working-tree-only

# Full: every released version, plus the working tree as 'dev'.
python scripts/docs_site/build_site.py --working-tree

# Released versions only (what CI runs):
python scripts/docs_site/build_site.py

python -m http.server 8765 --directory _site   # then open http://localhost:8765/
```

`BUILD_SITE_DIR` overrides the output directory (default `_site`). `--source
PATH` (or `$DOCS_SOURCE_REPO`) points the renderer at a different content repo —
its tags and `docs/` become the source of truth, while the templates, config,
and prose still come from this repo. It defaults to this repo for local preview.
The build generates the Pagefind search index automatically when `pagefind` (or
`npx`) is available; pass `--no-search` to skip it for faster local iteration.

## Deployment

The build runs in **this** (private) repo via `.github/workflows/docs-site.yml`,
so the generator is never published. The job checks out the **public** repo
(`nWave-ai/nWave`) with full history and renders every `vX.Y.Z` tag as a
snapshot via `--source`, then deploys `_site/` to Netlify. Only the rendered
HTML ships — never the build recipe.

It is triggered manually (`workflow_dispatch`) and by `release-prod.yml` /
`yank-release.yml` at the end (`workflow_call` + `secrets: inherit`), so the site
rebuilds automatically whenever the public tag set changes. Required secrets:
`RELEASETRAIN` (to check out the public repo), `NETLIFY_AUTH_TOKEN`,
`NETLIFY_SITE_ID`.

## Adding a new doc

Drop the markdown under `docs/guides/` or `docs/reference/` — it renders
automatically. To place it in the right sidebar quadrant, add its path to the
matching `sections` entry in `site.yaml`. Unclassified docs still render; they
just land under "More" (and the build logs them).
