# InDesign SVG Generator

A Python tool that generates A5 SVG pages for a book-like catalog. The SVGs are
the source-of-truth handoff to InDesign — they get imported (placed) into an
InDesign document for final print prep.

A local Flask preview server renders pairs of pages (left/right spread) in the
browser so layout iteration is fast: edit content → save → see the spread
refresh.

## Goals

- **Generate** one SVG per catalog page from a single content file.
- **Preview** two pages at a time in a browser, navigable via a slider on the
  left side of the page.
- **Hand off** SVGs to InDesign cleanly — text stays editable, images stay
  linked.

## Non-goals

- Not a print engine. We do not rasterize, color-manage, or produce PDFs here —
  InDesign owns that.
- Not a CMS. Content is authored by hand in a YAML file, not via a UI.
- Not a layout designer. Templates are written in code, not drag-and-drop.

## Page format

- **Size:** A5 portrait — **148mm × 210mm** (trim size).
- **Bleed:** **none.** The SVG canvas matches the trim exactly. If bleed is
  needed later, set `BLEED_MM` in `src/render.py` and the viewBox + canvas
  size derive from it automatically.
- **Margin (safe zone):** **14mm on all four sides**, measured from the trim
  edge. All text and critical content must stay inside the 120mm × 182mm
  content box.
- **SVG viewBox:** `0 0 148 210` (units in mm). Root `<svg>` sets
  `width="148mm" height="210mm"` so InDesign places it at the correct
  physical size.
- **Content box** (where text/critical art lives): top-left `(14, 14)`,
  bottom-right `(134, 196)`, size `120 × 182` mm.
- **Coordinate system:** millimeters, origin top-left of trim.

### Reference constants

Templates should pull these from `src/render.py` rather than redefining:

```python
TRIM_W_MM = 148
TRIM_H_MM = 210
BLEED_MM = 3
MARGIN_MM = 14

CANVAS_W_MM = TRIM_W_MM + 2 * BLEED_MM   # 154
CANVAS_H_MM = TRIM_H_MM + 2 * BLEED_MM   # 216

CONTENT_X_MM = MARGIN_MM                          # 14
CONTENT_Y_MM = MARGIN_MM                          # 14
CONTENT_W_MM = TRIM_W_MM - 2 * MARGIN_MM          # 120
CONTENT_H_MM = TRIM_H_MM - 2 * MARGIN_MM          # 182
```

## Design system

This is an **art-exhibition catalog** (Spanish). The visual system is fixed —
colors, fonts, and paragraph styles below are the source of truth. Do not
invent new ones in templates; pull from `src/styles.py`.

### Color palette

Define once in `src/styles.py` as `PALETTE`. Every `fill` and `stroke` in
generated SVGs should reference one of these by name — no inline hex literals
in templates.

| Name           | HEX       | RGB             | CMYK (approx.)   | Use                           |
|----------------|-----------|-----------------|------------------|-------------------------------|
| `rojo_tinta`   | `#A82A1F` | 168, 42, 31     | 22, 95, 100, 15  | Accent / red-background pages |
| `papel_crema`  | `#F5F2EB` | 245, 242, 235   | 3, 4, 8, 0       | Page background, reverse text |
| `negro_tinta`  | `#1A1A1A` | 26, 26, 26      | 0, 0, 0, 90      | Body text, titles             |
| `gris_texto`   | `#555555` | 85, 85, 85      | 0, 0, 0, 67      | Secondary text, captions      |
| `gris_claro`   | `#999999` | 153, 153, 153   | 0, 0, 0, 40      | Tertiary / disabled           |
| `frame_fill`   | `#EBE7DD` | 235, 231, 221   | —                | Image placeholder fill        |
| `frame_stroke` | `#C8C1B0` | 200, 193, 176   | —                | Image placeholder border      |

**Print note (for InDesign operator, not this tool):** for offset print, the
operator should map `rojo_tinta` to a Pantone equivalent (~**Pantone 7621 C**
or **Pantone 7600 C**) for chromatic consistency. Digital print can use the
CMYK values above directly. The SVG output always carries the HEX value — the
operator converts on import.

### Fonts

These must be installed on **both** the machine generating SVGs (irrelevant for
rendering since we don't rasterize, but the browser preview needs them) and
the InDesign machine. All free via Google Fonts:

| Family         | Weights used                        | Role                       |
|----------------|-------------------------------------|----------------------------|
| **Lato**       | Black, Regular, Italic              | Sans-serif: labels, titles |
| **EB Garamond**| Regular, Italic                     | Serif: body, captions      |
| **Caveat**     | Regular (Bold optional)             | Handwritten: pull-quotes   |

Downloads: fonts.google.com/specimen/Lato · fonts.google.com/specimen/EB+Garamond · fonts.google.com/specimen/Caveat

**Professional alternatives** (only if licensed): Inter / Univers / Helvetica
Neue / GT Walsheim in place of Lato; Adobe Caslon Pro / Sabon / Garamond
Premier Pro in place of EB Garamond; Homemade Apple / La Belle Aurore / Kalam
in place of Caveat. If swapped, update `PALETTE` font references in one place.

In SVG, reference the family by its exact PostScript / family name:
`font-family="Lato"`, `font-weight="900"` (Black), `font-style="italic"`.

### Text styles (paragraph styles)

These mirror the InDesign **Paragraph Styles** the operator will create. Define
in `src/styles.py` as `TEXT_STYLES: dict[str, TextStyle]`, keyed by the style
ID below (preserve the `NN-Section-Name` naming — it matches InDesign). Each
template applies a style by ID; no template inlines font/size/color.

```python
@dataclass(frozen=True)
class TextStyle:
    font_family: str
    font_weight: int = 400           # 400 regular, 700 bold, 900 black
    font_style: str = "normal"       # "normal" | "italic"
    size_pt: float = 10.0
    leading_pt: float | None = None  # absolute line height; None = auto
    tracking_per1000: int = 0        # InDesign tracking units (1/1000 em)
    color: str = "negro_tinta"       # PALETTE key
    uppercase: bool = False          # if True, pre-uppercase the string in Python
    align: str = "start"             # "start" | "middle" | "end"
    # paragraph-level (used by multi-paragraph templates)
    space_before_mm: float = 0.0
    space_after_mm: float = 0.0
    first_line_indent_mm: float = 0.0
    hanging_indent_mm: float = 0.0
    justified: bool = False          # SVG can't true-justify; see note below
```

#### Cover (`portada`)

| ID                       | Font / weight     | Size / leading | Tracking | Color         | Notes                          |
|--------------------------|-------------------|----------------|----------|---------------|--------------------------------|
| `01-Portada-Label`       | Lato Black        | 8 / 11 pt      | +200     | `rojo_tinta`  | UPPERCASE, align start         |
| `02-Portada-Titulo`      | Lato Black        | 42 / 40 pt     | -20      | `negro_tinta` | align start                    |
| `03-Portada-Subtitulo`   | EB Garamond Italic| 12 / 16 pt     |    0     | `gris_texto`  | align start; space_before 10mm |

#### Quote spread (`epigrafe`) — red background

| ID                       | Font / weight     | Size / leading | Tracking | Color         | Notes              |
|--------------------------|-------------------|----------------|----------|---------------|--------------------|
| `04-Epigrafe-Label`      | Lato Black        | 7 / 9 pt       | +200     | `papel_crema` | UPPERCASE, center  |
| `05-Epigrafe-Cita`       | EB Garamond Italic| 28 / 32 pt     |    0     | `papel_crema` | align start (per reference page 2) |
| `06-Epigrafe-Fuente`     | EB Garamond Italic| 8 / 12 pt      |    0     | `papel_crema` | align end          |

#### Curatorial note & index headers

| ID                       | Font / weight     | Size / leading | Tracking | Color         | Notes                                          |
|--------------------------|-------------------|----------------|----------|---------------|------------------------------------------------|
| `07-Seccion-Label`       | Lato Black        | 7 / 9 pt       | +200     | `rojo_tinta`  | UPPERCASE                                      |
| `08-Seccion-Titulo`      | Lato Black        | 22 / 23 pt     | -10      | `negro_tinta` | space_after 12mm                               |
| `09-Body-Garamond`       | EB Garamond Reg.  | 10 / 15.5 pt   |    0     | `negro_tinta` | justified; first-line indent 5mm (skip 1st ¶)  |

#### Index (`indice`)

| ID                       | Font / weight     | Size / leading | Color         | Notes        |
|--------------------------|-------------------|----------------|---------------|--------------|
| `10-Indice-Romano`       | EB Garamond Reg.  | 16 pt          | `rojo_tinta`  |              |
| `11-Indice-Sala`         | Lato Black        | 11 / 14 pt     | `negro_tinta` |              |
| `12-Indice-Periodo`      | EB Garamond Italic| 9 pt           | `gris_texto`  | align end    |

#### Room title page (`portadilla de sala`) — red background

| ID                       | Font / weight     | Size / leading | Tracking | Color         | Notes               |
|--------------------------|-------------------|----------------|----------|---------------|---------------------|
| `13-Portadilla-Romano`   | EB Garamond Reg.  | 180 / 155 pt   |    0     | `papel_crema` | align start         |
| `14-Portadilla-Nombre`   | Lato Black        | 20 / 22 pt     | -10      | `papel_crema` | space_before 6mm    |
| `15-Portadilla-Periodo`  | Lato Black        | 8 / 10 pt      | +200     | `papel_crema` | UPPERCASE           |
| `16-Portadilla-CitaCurato`| EB Garamond Italic | 13 / 18 pt   |    0     | `papel_crema` | align start (per reference page 6) |

#### Artwork cards (`fichas`) — both pages of the spread

| ID                          | Font / weight     | Size / leading | Tracking | Color         | Notes                |
|-----------------------------|-------------------|----------------|----------|---------------|----------------------|
| `17-Ficha-Cabecera-ID`      | Lato Black        | 6.5 / 9 pt     | +150     | `rojo_tinta`  | UPPERCASE            |
| `18-Ficha-Cabecera-Sub`     | Lato Black        | 6.5 / 9 pt     | +150     | `gris_texto`  | UPPERCASE, align end |
| `19-Ficha-Tipo`             | EB Garamond Italic| 8.5 / 11 pt    |    0     | `rojo_tinta`  |                      |
| `20-Ficha-Titulo-Pieza`     | Lato Black        | 20 / 20 pt     | -15      | `negro_tinta` |                      |
| `21-Ficha-Subtitulo-Autor`  | EB Garamond Italic| 9 / 12 pt      |    0     | `negro_tinta` |                      |
| `22-Ficha-Subtitulo-Datos`  | EB Garamond Reg.  | 9 / 12 pt      |    0     | `gris_texto`  |                      |
| `23-Ficha-Epigrafe-Imagen`  | EB Garamond Italic| 7.5 / 10 pt    |    0     | `gris_texto`  |                      |
| `24-Ficha-Descripcion`      | EB Garamond Reg.  | 10 / 15 pt     |    0     | `negro_tinta` | justified            |
| `25-Ficha-CitaTextual`      | EB Garamond Italic| 14 / 18 pt     |    0     | `rojo_tinta`  | align start (per reference page 8) |
| `26-Ficha-Fuente`           | Lato Regular      | 6.5 / 10 pt    | +50      | `gris_texto`  |                      |

#### Bibliography (`bibliografía`)

| ID                       | Font / weight     | Size / leading | Color         | Notes                              |
|--------------------------|-------------------|----------------|---------------|------------------------------------|
| `27-Biblio-Referencia`   | EB Garamond Reg.  | 9 / 13.5 pt    | `negro_tinta` | justified; hanging indent 5mm      |

### Unit conversions (InDesign → SVG)

The table values use InDesign conventions. Templates must convert:

- **Font size:** use the `pt` unit directly on `font-size` (e.g.
  `font-size="10pt"`). SVG accepts mixed units; the mm-based viewBox does not
  interfere.
- **Leading (interlineado):** InDesign leading is absolute pt. SVG multi-line
  text uses `<tspan x="X" dy="LEADING_pt">…</tspan>` for each subsequent line.
  Set `dy="0"` on the first line. Do **not** rely on CSS `line-height` — not
  all SVG renderers honor it, and InDesign ignores it on import.
- **Tracking:** InDesign tracking is 1/1000 em. Convert to SVG
  `letter-spacing` in pt: `letter_spacing_pt = tracking_per1000 / 1000 *
  size_pt`. Example: +200 tracking at 8pt → `letter-spacing="1.6pt"`.
- **Uppercase:** pre-uppercase the string in Python before placing it in the
  SVG. Do **not** use CSS `text-transform` — InDesign discards it.
- **Alignment:** SVG `text-anchor` is `start | middle | end`. Compute the
  anchor position from the column box; do not rely on auto-flow.
- **Justified text** (`09-Body-Garamond`, `24-Ficha-Descripcion`,
  `27-Biblio-Referencia`): SVG cannot true-justify. The generator renders
  these **ragged** for preview; the InDesign operator re-flows them with
  proper justification on import. Document this in the preview UI so it's not
  confused with a bug.
- **Color:** resolve PALETTE key → hex; emit as
  `fill="#A82A1F"` (presentation attribute, not CSS).

### Graphic elements

Reusable helpers in `src/render.py`, parameterized by position. All use
PALETTE colors.

- **Red vertical rule (decorative):** filled rect, **2.5mm wide**, height
  varies (10–30mm on fichas, 60mm on cover), fill `rojo_tinta`, no stroke.
  Helper: `red_rule_vertical(x_mm, y_mm, height_mm)`.
- **Ficha header horizontal rule:** line, stroke `negro_tinta`, **0.4pt**
  width, length = content width (120mm by default; use 118mm if you reserve a
  1mm gutter). Helper: `ficha_header_rule(y_mm, length_mm=120)`.
- **Ficha footer top rule:** line, stroke `rojo_tinta`, **0.3pt** width, same
  length as the header rule. Helper: `ficha_footer_rule(y_mm, length_mm=120)`.
- **Image placeholder frame:** rect, fill `frame_fill` (#EBE7DD), stroke
  `frame_stroke` (#C8C1B0), **0.4pt** stroke, **no corner radius**. Used while
  the real image is missing or for layout proofing. Helper:
  `image_placeholder(x_mm, y_mm, w_mm, h_mm)`.
- **Curly bracket `{` for image captions:** rendered as a `<text>` element
  using EB Garamond, **2–3pt larger** than the adjacent caption text, fill
  `rojo_tinta`, with **1.5mm right margin** before the caption begins. Helper:
  `caption_bracket(x_mm, y_mm, adjacent_size_pt)`.

## Content source

A **single YAML file** at `content/catalog.yaml` describes every page. Shape:

```yaml
meta:
  title: "Catálogo de Exposición"

pages:
  - id: 1
    template: portada
    data:
      label: "Catálogo"
      titulo: "Nombre de la Exposición"
      subtitulo: "Subtítulo descriptivo del proyecto curatorial"

  - id: 2
    template: epigrafe
    data:
      label: "Epígrafe"
      cita: "Texto manuscrito de la cita."
      fuente: "— Autor, Obra, año"

  - id: 4
    template: portadilla_sala
    data:
      romano: "I"
      nombre: "Sala Uno"
      periodo: "1920 — 1935"
      cita_curatorial: "Texto curatorial breve."

  - id: 6
    template: ficha
    data:
      cabecera_id: "Sala I · Pieza 01"
      cabecera_sub: "Óleo sobre tela"
      tipo: "Pintura"
      titulo_pieza: "Título de la Obra"
      autor: "Nombre del Autor"
      datos: "1925, 80 × 60 cm, colección X"
      image: "images/pieza-01.jpg"
      epigrafe_imagen: "Vista de la obra en sala."
      descripcion: "Texto descriptivo justificado…"
      cita_textual: "Cita breve del artista."
      fuente: "Catálogo razonado, 1998"
```

Page IDs should be contiguous starting at 1 (page 1 = right page of the opening
spread by print convention; spreads are then 2-3, 4-5, ...). The preview UI
pairs them this way.

## Templates

The catalog uses these templates (one Python file each in `src/templates/`):

- `portada` — cover.
- `epigrafe` — full-bleed red-background quote spread.
- `nota_curatorial` — curatorial essay (body text).
- `indice` — index / contents.
- `portadilla_sala` — room title page (red background).
- `ficha` — artwork card (typically a two-page spread: image left, data right).
- `bibliografia` — references list.

Each template is a Python function that takes a `data` dict and returns an SVG
string (or an `lxml`/`svgwrite` tree). Register new templates in
`src/templates/__init__.py` so `template: foo` in YAML resolves to a renderer.

Template responsibilities:
- Draw the page chrome (page number, header, etc.).
- Apply text via the `TEXT_STYLES` registry — no inline font/size/color.
- Use `PALETTE` keys for fills/strokes — no inline hex literals.
- Place text using `<text>` elements — **never convert to paths**.
- Reference images via `<image href="../images/foo.jpg">` with a **relative
  path** so InDesign links them (does not embed).

## InDesign import constraints (load-bearing)

These are firm requirements — they shape the SVG output:

- **Text stays as `<text>` elements.** Do not outline/path-convert text. The
  InDesign operator needs to be able to edit copy after import. The fonts
  referenced in the SVG must be installed on the InDesign machine.
- **Images are linked, not embedded.** Use `<image href="relative/path.jpg">`
  with a path that resolves from the SVG's location. Do **not** base64-encode.
  Keep the `images/` directory shipped alongside the `out/` SVGs so the
  relative paths still resolve when the SVGs are moved into the InDesign
  project folder.
- Use real font family names that exist in InDesign (e.g. `"Helvetica"`, not
  web-only stacks).
- Avoid SVG features InDesign chokes on: filters, masks beyond basic clipping,
  CSS-only styling. Prefer presentation attributes (`fill="..."`,
  `font-family="..."`) over `<style>` blocks.

## Project layout

```
in-design-svg-generator/
├── CLAUDE.md
├── pyproject.toml          # uv / pip project file
├── content/
│   └── catalog.yaml        # source of truth for all page content
├── images/                 # source images, referenced by relative path
├── out/                    # generated SVGs (page-001.svg, page-002.svg, ...)
├── src/
│   ├── __init__.py
│   ├── generate.py         # CLI: read YAML, render each page → out/
│   ├── render.py           # core SVG-building helpers (mm units, A5 frame, graphic elements)
│   ├── styles.py           # PALETTE + TEXT_STYLES registries (design system)
│   ├── templates/
│   │   ├── __init__.py     # template registry
│   │   ├── cover.py
│   │   ├── section_divider.py
│   │   └── product.py
│   └── server.py           # Flask preview server with live reload
└── tests/
    └── test_templates.py
```

## Stack

- **Python 3.11+**
- **PyYAML** — parse the content file.
- **svgwrite** or hand-rolled string templating via `lxml` — pick one and stick
  with it. `svgwrite` is friendlier for structured output; raw strings are
  fine if templates stay small.
- **Flask** — preview server.
- **livereload** (or Flask + a small WebSocket reloader) — auto-refresh browser
  on file change.
- **watchdog** — file watcher feeding the reloader.

## Preview server

Run with `python -m src.server` (or a `pyproject.toml` script entry).

Behavior:
- Serves a single page at `/` showing a **two-page spread**: page N on the
  left, page N+1 on the right.
- **Slider on the left edge** of the page selects the spread. Snaps to valid
  spread starts (1, 2, 4, 6, ...). Keyboard arrows also page through.
- Watches `content/catalog.yaml`, `images/`, and `src/templates/` — on change,
  regenerates affected SVGs and pushes a reload to the browser.
- The two pages are rendered as `<object data="page-N.svg">` or inline SVG so
  text remains selectable in the preview (good sanity check that text didn't
  accidentally get outlined).

## CLI

- `python -m src.generate` — regenerate all SVGs into `out/`.
- `python -m src.generate --page 3` — regenerate one page.
- `python -m src.server` — start preview server (also regenerates on start).

## Conventions

- **Units are millimeters everywhere.** No pixels. If a template helper takes a
  number, it's mm. Name variables accordingly (`margin_mm = 10`).
- **Filenames:** `out/page-001.svg`, zero-padded to 3 digits so they sort right
  in Finder and InDesign's Place dialog.
- **Coordinates:** top-left origin, Y increases downward (SVG default).
- **Don't** add per-page Python files. Pages are data; templates are code.

## Open decisions (resolve before first real layout)

- Image color space: source images should be CMYK/RGB? InDesign will convert,
  but consistent source helps. (Not enforced by this tool.)
- Pantone mapping for `rojo_tinta` — confirm whether the print run is offset
  (use Pantone 7621 C / 7600 C) or digital (CMYK values stand).
