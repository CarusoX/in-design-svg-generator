# Archivo de lo No Conservado — SVG Catalog Generator

Python tool that generates A5 SVG pages for an art-exhibition catalog
("Archivo de lo No Conservado", Spanish, Latin-American graphic design)
from a single YAML content file. Renders pairs of pages in a browser
for live iteration, and bundles the whole thing into a print-ready PDF
of A4-landscape spreads.

The SVGs are the source-of-truth handoff to InDesign — they get
imported (placed) into an InDesign document for final print prep.
Text stays editable (`<text>` elements, not paths); images stay
linked (`<image href>` with relative paths).

> The exhaustive design-system spec — palette, fonts, paragraph styles,
> InDesign import constraints — lives in [`CLAUDE.md`](CLAUDE.md). This
> README focuses on **how to run the thing** and **what to look at when
> you come back to it later**.

## Quick start

```bash
# Install (Python 3.11+)
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# System tools (Homebrew on macOS) — needed for the PDF build
brew install librsvg poppler

# Generate every page into out/
.venv/bin/python -m src.generate

# Live preview in the browser
.venv/bin/python -m src.server          # → http://localhost:5000

# Bundle the whole catalog into one PDF
.venv/bin/python -m src.build_pdf       # → out/catalog.pdf
```

## Commands

| Command | What it does |
|---|---|
| `python -m src.generate` | Reads `content/catalog.yaml`, renders every page to `out/page-NNN.svg`, copies images from `reference/imagenes/` to `out/images/`, writes the reticle overlay `out/_reticle.svg`. |
| `python -m src.generate --page N` | Re-renders just page N (skips the `out/` cleanup). Fast feedback loop while iterating one page. |
| `python -m src.server` | Flask preview server with livereload. Shows two-page spreads, navigable via a left-edge slider and arrow keys; auto-regenerates affected SVGs when YAML / templates / styles / render.py change. |
| `python -m src.build_pdf` | Composes `out/page-*.svg` into A4-landscape spreads and outputs `out/catalog.pdf`. Requires `rsvg-convert` (librsvg) and `pdfunite` (poppler-utils). |

`pyproject.toml` exposes the first two as `catalog-generate` / `catalog-serve`
scripts as well.

## What's where

```
in-design-svg-generator/
├── CLAUDE.md                    Full design-system spec (palette, fonts,
│                                paragraph styles, InDesign constraints).
├── README.md                    This file.
├── pyproject.toml               Deps + console scripts.
├── content/
│   ├── catalog.yaml             SINGLE source of truth: every page's data,
│   │                            keyed by section (portada, epigrafe,
│   │                            nota_curatorial, indice, salas[…], biblio).
│   ├── source.json              Original curator hand-off (untouched
│   │                            reference; YAML was built from this).
│   └── rooms/                   (Per-room reference materials.)
├── reference/
│   └── imagenes/                Source images (curator-authored). Get
│                                copied into out/images/ on each build.
├── out/                         Build output — page-001.svg .. page-NNN.svg,
│                                _reticle.svg overlay, images/ bundle,
│                                catalog.pdf when built.
├── src/
│   ├── generate.py              CLI + section-based catalog compiler.
│   │                            Walks YAML sections → flat page list with
│   │                            sequential IDs. Owns parity rules (e.g.
│   │                            portadilla_sala MUST land on an even page).
│   ├── render.py                Core SVG-building helpers: A5 frame,
│   │                            mm units, text & word-wrap, hyphenation,
│   │                            graphic primitives, font metrics (Pillow).
│   ├── styles.py                Design-system source of truth: PALETTE
│   │                            (color names → hex) and TEXT_STYLES
│   │                            (paragraph-style registry keyed by ID).
│   ├── layouts.py               Guillotine packer for variable-size
│   │                            image slots on ficha_imagen pages.
│   ├── server.py                Flask preview + livereload watcher.
│   ├── build_pdf.py             Spreads composer → catalog.pdf.
│   ├── web_templates/index.html Preview UI shell (slider, spread view).
│   └── templates/               One Python file per page template (see
│                                "Templates" below). Each is a function
│                                `render(page_id, data) -> str`.
├── tests/
│   ├── test_section1.py         Visual regression: renders the Sala I
│   │                            portadilla and compares to the InDesign
│   │                            export in ground-truth/Section1.svg.
│   └── ground-truth/            Reference SVGs from the design team.
└── vendor/
    └── fonts/                   Google's variable EB Garamond TTFs,
                                 used by Pillow for measurement so wrap
                                 widths match what the browser actually
                                 renders. See "Fonts" below.
```

## How content flows

1. **YAML** (`content/catalog.yaml`) holds the catalog as semantic
   sections (`portada`, `epigrafe`, `nota_curatorial`, `indice`,
   `salas[…]`, `bibliografia`). It does **not** know about page numbers
   — those are derived.
2. **`src/generate._compile_pages`** walks the YAML and emits a flat
   list of pages with sequential `id`s. This is where the per-template
   pagination calls live (`nota_curatorial.paginate`,
   `bibliografia.paginate`) — long sections expand to as many pages as
   they need, and the IDs of everything downstream shift automatically.
3. **Templates** in `src/templates/*.py` each export `render(page_id,
   data) -> str` and are registered in `src/templates/__init__.py`.
   Each template returns a full `<svg>…</svg>` document.
4. **`out/page-NNN.svg`** is the per-page output. The reticle overlay
   (`out/_reticle.svg`) is preview-only chrome — never imported into
   InDesign.
5. **`src/build_pdf.py`** pairs the SVGs into spreads (mirroring the
   server's left/right layout) and emits a single PDF for proofing.

Image paths in YAML are relative to `reference/imagenes/`. `sync_images()`
copies the actual files into `out/images/` so the SVGs' relative
`<image href="images/…">` references resolve when the operator moves
the whole `out/` directory into their InDesign project.

## Templates

Each template is a self-contained file in `src/templates/`. Layout
geometry is computed from the reticle helpers in `_ficha_common.py`,
never from magic numbers in the page.

| Template | Purpose |
|---|---|
| `portada` | Cover page. Full-bleed `rojo_tinta`, Lato Bold title + EB Garamond italic subtitle, both anchored to the reticle. |
| `epigrafe` | Full-bleed red quote spread. Centered quote in cols 2–5, source line anchored to row 7 bottom. |
| `nota_curatorial` | Curatorial essay. **Paginates dynamically**: a single body string in YAML wraps into as many pages as needed; references in parentheses auto-italicize; closing paragraph is a 10pt italic colophon anchored to row 7 top. See `paginate()` in the file. |
| `indice` | Table of contents. Sala rows with romano, name, date range, and auto-computed page numbers. |
| `portadilla_sala` | Per-room title page. Red background, huge roman numeral, sala name, curator quote. **Must land on an even page** — `generate.py` raises if parity drifts. |
| `blank_red` | Right-facing companion to a portadilla so the following pieza spread starts cleanly. |
| `blank_cream` | Parity padder for the front matter when `nota_curatorial` ends on an odd page. |
| `ficha_imagen` | Image-only side of a pieza spread. Uses `src/layouts.py`'s guillotine packer for multi-image slots. |
| `ficha_texto` | Text side of a pieza spread (metadata, title block, description). |
| `bibliografia` | References list. **Paginates dynamically**; URL chunks render as one continuous string with underline, and break at any of `/ _ . ? & = -` (the dash attaches to the SUFFIX so a wrap doesn't look like soft hyphenation). |
| `placeholder` | Fallback for any `template:` in YAML that isn't registered yet. Shows what's missing during early development. |

## Design system

Full spec in [`CLAUDE.md`](CLAUDE.md). The two things to remember:

- **All colors come from `PALETTE`** in `src/styles.py` (`rojo_tinta`,
  `papel_crema`, `negro_tinta`, `gris_texto`, `gris_claro`,
  `frame_fill`, `frame_stroke`). No inline hex in templates.
- **All text uses a style ID** from `TEXT_STYLES` (`02-Portada-Titulo`,
  `09-Body-Garamond`, etc.). The numeric prefix matches the InDesign
  Paragraph Styles panel order the operator will create. No inline
  font / size / color in templates.

## Reticle

A 6-col × 9-row grid inset 1.4 mm inside the 14 mm safe margin, with
4 mm gutters between cells. Lives in `src/render.py` as constants and
in `src/templates/_ficha_common.py` as helpers:

```python
ch.row_top(n)      # absolute Y of the top edge of row n (1-indexed)
ch.row_bottom(n)   # absolute Y of the bottom edge of row n
ch.LEFT_X_MM       # x of the first vertical reticle line  (= 15.4)
ch.RIGHT_X_MM      # x of the last vertical reticle line   (= 132.6)
r.RETICLE_COL_RIGHT_X_MM[i]   # x of column i+1's right edge (0-indexed list)
```

Conventions used across every template:

- Rows/cols are **1-indexed** in text and template constants.
- **"Cap-top on row top"** = `baseline = row_top(n) + cap_h`. That puts
  the first line of text visually sitting on the row's top edge.
- **"Baseline on row bottom"** = `baseline = row_bottom(n)`. Used for
  titles like `Indice-Titulo` and the cover title's last line.
- **"X mm gap"** in geometry comments means the **visible** gap
  (descender-to-cap-top), not baseline-to-baseline. The actual baseline
  math has the cap-h / descender added in.
- Cap-height ratios: EB Garamond `0.685`em, Lato `0.72`em.
  Descender: `0.21`em (both).

The reticle is rendered to `out/_reticle.svg` for preview overlay only;
it never gets bundled into the InDesign handoff.

## Fonts

The browser preview loads Caveat + Lato from Google Fonts; EB Garamond
is resolved through the SVG `font-family` chain to the system's
installed family (Homebrew's `EBGaramond12-Regular.otf` on the dev
machine).

**Pillow** (used by `render._measure_word_mm` for wrap calculations)
measures against the variable EB Garamond TTFs vendored at
`vendor/fonts/`:

```
vendor/fonts/EBGaramond-VariableFont_wght.ttf
vendor/fonts/EBGaramond-Italic-VariableFont_wght.ttf
```

These are Google Fonts' modern variable family — the **same** family
the browser would render if it had access. They are a touch wider
per glyph than the locally-installed `EBGaramond12-Regular.otf`. Using
them for measurement keeps the wrap calculation in lockstep with what
the browser actually paints, so lines don't quietly spill past the
right reticle edge.

If you ever swap fonts, update both:

1. `_font_path()` in `src/render.py` (Pillow measurement).
2. `font_family_css()` in `src/render.py` (the chain emitted into the
   SVG `font-family` attribute).

## Build PDF

```bash
.venv/bin/python -m src.build_pdf
```

For each spread, the script builds a composite A4-landscape SVG that
inlines the spread's two A5 pages as nested `<svg>` elements. The
composite is written into `out/` so the embedded page SVGs' relative
`<image href="images/…">` references still resolve (since `out/images/`
is where `sync_images()` puts them). `rsvg-convert -f pdf` renders each
composite to a single-page PDF, then `pdfunite` concatenates them into
`out/catalog.pdf`.

**Font pinning** (matters on macOS): the script invokes `rsvg-convert`
with two env vars set together — `PANGOCAIRO_BACKEND=fc` and a custom
`FONTCONFIG_FILE` pointing at a temp config that prepends
`vendor/fonts/` to fontconfig's search path. Without the Pango
override, librsvg uses Pango's CoreText backend on Mac and silently
ignores `FONTCONFIG_FILE`, so the user's locally-installed
`EBGaramond12-Italic.otf` wins the family match and ends up in the
PDF — visibly different from the Google variable family the browser
preview uses and Pillow measures against. With both env vars set,
the PDF embeds `EBGaramond-Italic` / `EBGaramond-Regular` (the
vendored variable family) and matches the preview exactly. See
`src/build_pdf._rsvg_env` for the gory details.

Spread layout mirrors the server's preview: opening spread is
`(blank, page-1)`; subsequent spreads pair `(2,3), (4,5), …`. The
final spread may be `(last-even-page, blank)` if the catalog ends on
an even page.

Output is roughly 1 MB per spread (images embedded as rasterised
streams). The 108-page catalog produces a ~65 MB PDF.

## Conventions / gotchas (the stuff that took a while to get right)

- **Units are millimeters everywhere.** Number with no unit suffix in
  Python code means mm. `render.MM_PER_PT` / `PT_PER_MM` are for the
  rare conversion (font sizes from styles come in pt and need
  converting to mm before being emitted as unitless values in the
  mm-based viewBox).
- **Justified text is rendered ragged.** SVG can't true-justify, and
  the per-word-`<tspan>` hack we tried first ate visible spaces after
  commas. Body paragraph styles (`09-Body-Garamond`,
  `27-Biblio-Referencia`) are left-aligned with `pyphen` hyphenation;
  the InDesign operator re-flows them with proper justification on
  import. If you ever flip `justified=True` back on a style, expect
  the comma-space bug on lines with parentheticals.
- **First-line indent steals from the wrap budget.** When a paragraph
  has a `sangría` (first-line indent), the wrap target for line 1
  must subtract the indent — otherwise line 1 fills the full reticle
  width AND the indent, spilling past the right column.
  `nota_curatorial._wrap_rich` handles this via `first_line_indent_mm`.
- **URL splitting in `bibliografia`** breaks at `/ _ . ? & = -`, but
  `-` attaches to the **suffix** side of the break so a wrap doesn't
  end with a dangling dash that reads as soft hyphenation. URL chunks
  are marked `sticky=True` so the wrap measures them without an
  inter-token space, and the renderer joins them back without a space
  so the URL reads as one continuous string.
- **URL underline uses native `text-decoration="underline"`** so the
  browser pulls the font's own underline metrics. The earlier custom
  `<line>`-based underline (to clear the underscore-vs-underline
  collision) didn't look as good as the font-native one; the user
  preferred the trade-off of underscore conflict over the manual line.
- **Parity rules** (`generate.py`): `portadilla_sala` must land on an
  even page (left of spread). The compiler raises `SystemExit` if it
  drifts. When you add / remove pages in the front matter, the auto
  pagination on `nota_curatorial` + the `blank_cream` padder keep the
  count even.

## Authoring loop

Typical iteration:

```bash
# Terminal 1 — preview server (auto-reloads on YAML / src changes)
.venv/bin/python -m src.server

# Terminal 2 — keep this open for one-off page rebuilds during heavy
# template work
.venv/bin/python -m src.generate --page 7
```

Edit `content/catalog.yaml` for content; edit `src/templates/*.py` for
layout. Both trigger a regenerate-and-reload in the browser.

When the layout is locked in, build the PDF for review:

```bash
.venv/bin/python -m src.generate
.venv/bin/python -m src.build_pdf
open out/catalog.pdf
```

## Handing off to InDesign

The operator imports the SVGs from `out/` (place via File ▸ Place).
Critical constraints (from `CLAUDE.md`):

- Text stays as `<text>` (never outlined to paths) — operator can edit
  copy after import. The fonts referenced in the SVG must be installed
  on the InDesign machine.
- Images are linked via `<image href="images/…">` with relative paths.
  Move the entire `out/` directory (including `out/images/`) into the
  InDesign project folder so the links resolve.
- Avoid SVG features InDesign chokes on: filters, masks beyond basic
  clipping, CSS-only styling. We use presentation attributes
  (`fill="…"`, `font-family="…"`) throughout.

The `Indice-Titulo`, `02-Portada-Titulo`, `08-Seccion-Titulo` etc.
naming exactly matches the Paragraph Styles panel the operator builds
in InDesign — preserve those IDs when adding new styles.
