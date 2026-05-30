"""Ficha — text side of an artwork spread.

After the v2 refactor the text page can land on EITHER side of a
spread, alternating per pieza within a sala (so the red image pages
back-to-back across the spine form full-red leaves every other
sheet — see `generate._compile_pages`). The typographic layout stays
identical on both orientations — only the rojo_tinta bleed strip
moves to whichever edge is the spine, so the red continues from the
adjacent image page across the binding.

Layout:
- No cabecera; folio at the page's outer edge (handled by
  `r.folio()` via page parity).
- 4 unlabeled metadata lines (Fecha / Origen / Autor / Estado) in
  row 1, left-anchored at col 1.
- A thin (0.8mm) rojo_tinta rule on the right edge of col 1, 2 rows
  tall. Title in Lato Bold starting at col 2, with the LAST line's
  baseline at the bottom of row 4.
- `tipo` as a bold uppercase red label (07-Seccion-Label) at row 6.
- 2-column description body below (cols 1-3 + cols 4-6), reading
  left → right top → bottom regardless of which side of the spread
  the page is on.
- 7mm rojo_tinta bleed strip on the SPINE side: right edge for
  even/left-of-spread pages, left edge for odd/right-of-spread pages.

Expected `data` keys:
    pieza_id (str)       — surfaced via bridged YAML, not rendered
    cabecera_sub (str)   — bridged, unused (kept for compat)
    autor (str)          — bridged from imagen block
    estado (str)         — from texto block
    datos (str)          — bridged; split by " · " into fecha + origen
    tipo (str)           — bridged from imagen block
    titulo (str)         — bridged from imagen block
    descripcion (str)    — multi-line body, 2-col wrap + hyphenation
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


# ── Horizontal anchors (computed for the DEFAULT layout; mirrored at
# render time when the text page lands on an odd page) ───────────────

META_X_MM = ch.LEFT_X_MM                       # 15.4 (start of col 1)
META_MAX_W_MM = ch.RIGHT_X_MM - META_X_MM      # 117.2 (col 1 → col 6 right edge)
RULE_W_MM = 0.8                                 # "much thinner" red rule
COL_1_RIGHT_X_MM = r.RETICLE_COL_RIGHT_X_MM[0]  # right edge of col 1
RULE_X_MM = COL_1_RIGHT_X_MM - RULE_W_MM        # rule's right edge IS col 1's right
TITLE_X_MM = COL_1_RIGHT_X_MM + r.RETICLE_GUTTER_MM  # left edge of col 2
TITLE_MAX_W_MM = ch.RIGHT_X_MM - TITLE_X_MM     # col 2 through col 6

BODY_X_MM = ch.LEFT_X_MM
_HALF_COLS = 3
BODY_COL_W_MM = (
    _HALF_COLS * r.RETICLE_COL_W_MM
    + (_HALF_COLS - 1) * r.RETICLE_GUTTER_MM
)
BODY_GUTTER_MM = r.RETICLE_GUTTER_MM

# Half the content inset (trim edge → where the columns start), not half
# the bare page margin — so the strip lines up with the text block.
#   (MARGIN_MM + RETICLE_INSET_MM) / 2 = (14 + 1.4) / 2 = 7.7
BLEED_W_MM = (r.MARGIN_MM + r.RETICLE_INSET_MM) / 2
BLEED_Y_MM = 0.0
BLEED_H_MM = r.TRIM_H_MM

# ── Vertical layout (mirror-invariant) ───────────────────────────────

_GARAMOND_CAP_RATIO = 0.685
_GARAMOND_DESC_RATIO = 0.21
_LATO_CAP_RATIO = 0.72

META_FIRST_BASELINE_Y_MM = (
    ch.row_top(1)
    + _GARAMOND_CAP_RATIO * TEXT_STYLES["Ficha-Meta-Top"].size_pt * r.MM_PER_PT
)
META_LEADING_MM = (
    (TEXT_STYLES["Ficha-Meta-Top"].leading_pt or
     TEXT_STYLES["Ficha-Meta-Top"].size_pt * 1.2) * r.MM_PER_PT
)

_TITLE_STYLE = TEXT_STYLES["20-Ficha-Titulo-Pieza"]
_TITLE_LEADING_MM = (
    (_TITLE_STYLE.leading_pt or _TITLE_STYLE.size_pt * 1.2) * r.MM_PER_PT
)
TITLE_LAST_BASELINE_Y_MM = ch.row_bottom(4)
RULE_TOP_Y_MM = ch.row_top(3)
RULE_BOTTOM_Y_MM = ch.row_bottom(4)
RULE_H_MM = RULE_BOTTOM_Y_MM - RULE_TOP_Y_MM

TIPO_LABEL_STYLE_ID = "07-Seccion-Label"
TIPO_CAP_TOP_Y_MM = ch.row_top(6)
TIPO_BASELINE_Y_MM = (
    TIPO_CAP_TOP_Y_MM
    + _LATO_CAP_RATIO * TEXT_STYLES[TIPO_LABEL_STYLE_ID].size_pt * r.MM_PER_PT
)
_TIPO_DESC_MM = (
    TEXT_STYLES[TIPO_LABEL_STYLE_ID].size_pt * _GARAMOND_DESC_RATIO * r.MM_PER_PT
)

_BODY_GAP_MM = 4.0
_BODY_STYLE_ID = "24-Ficha-Descripcion"
_BODY_CAP_H_MM = (
    _GARAMOND_CAP_RATIO * TEXT_STYLES[_BODY_STYLE_ID].size_pt * r.MM_PER_PT
)
BODY_BASELINE_Y_MM = (
    TIPO_BASELINE_Y_MM + _TIPO_DESC_MM + _BODY_GAP_MM + _BODY_CAP_H_MM
)


def render(page_id: int, data: dict) -> str:
    titulo = str(data.get("titulo", "")).strip()
    tipo = str(data.get("tipo", "")).strip()
    descripcion = str(data.get("descripcion", "")).strip()
    autor = str(data.get("autor", "")).strip()
    estado = str(data.get("estado", "")).strip()
    datos = str(data.get("datos", "")).strip()
    if " · " in datos:
        fecha, origen = (s.strip() for s in datos.split(" · ", 1))
    else:
        fecha, origen = datos, ""

    # The ONLY thing that flips with page parity is the bleed strip:
    # it sits on the spine side so the red continues from the adjacent
    # image page across the binding.
    #   even page (left of spread):  spine = right edge → bleed right
    #   odd page  (right of spread): spine = left edge  → bleed left
    bleed_x = 0.0 if (page_id % 2 == 1) else (r.TRIM_W_MM - BLEED_W_MM)

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Bleed strip on the spine side (matches the facing image page's
    #   background, including any per-artwork `fondo:` override)
    parts.append(
        f'<rect x="{bleed_x}" y="{BLEED_Y_MM}" '
        f'width="{BLEED_W_MM}" height="{BLEED_H_MM}" '
        f'fill="{ch.resolve_fondo(data)}"/>'
    )

    # — Metadata stack (4 unlabeled lines, left-anchored at col 1)
    parts.append(_metadata_stack([fecha, origen, autor, estado]))

    # — Title block: thin red rule + title. Last line's baseline at
    # row_bottom(4); multi-line titles stack upward. Never hyphenate.
    if titulo:
        parts.append(r.red_rule_vertical(
            RULE_X_MM, RULE_TOP_Y_MM, RULE_H_MM, width_mm=RULE_W_MM,
        ))
        n_lines = len(r.wrap_lines(
            titulo, _TITLE_STYLE, TITLE_MAX_W_MM, hyphenate=False,
        ))
        first_baseline = TITLE_LAST_BASELINE_Y_MM - (n_lines - 1) * _TITLE_LEADING_MM
        parts.append(r.text(
            "20-Ficha-Titulo-Pieza", titulo,
            x_mm=TITLE_X_MM, y_mm=first_baseline,
            max_width_mm=TITLE_MAX_W_MM,
            hyphenate=False,
        ))

    # — Tipo as bold uppercase label
    if tipo:
        parts.append(r.text(
            TIPO_LABEL_STYLE_ID, tipo,
            x_mm=BODY_X_MM, y_mm=TIPO_BASELINE_Y_MM,
        ))

    # — 2-column description (always left → right reading order)
    if descripcion:
        svg, _ = r.paragraph_two_column(
            _BODY_STYLE_ID, descripcion,
            x_mm=BODY_X_MM, y_mm=BODY_BASELINE_Y_MM,
            col_w_mm=BODY_COL_W_MM, gutter_mm=BODY_GUTTER_MM,
        )
        parts.append(svg)

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)


def _metadata_stack(values: list[str]) -> str:
    """Stack of italic gray lines (no labels) at top-left of col 1.
    Empty values are skipped so the stack closes up rather than
    leaving a gap. Each value wraps with Spanish hyphenation at the
    full reticle width (col 1 → col 6 right edge), so long autors etc.
    flow into a second/third line instead of overrunning the page."""
    items = [v for v in values if v]
    if not items:
        return ""
    style = TEXT_STYLES["Ficha-Meta-Top"]
    fill = r.PALETTE[style.color]
    size_mm = style.size_pt * r.MM_PER_PT
    parts = [
        f'<text x="{META_X_MM}" y="{META_FIRST_BASELINE_Y_MM:.4f}" '
        f'font-family="{r.font_family_css(style.font_family)}" '
        f'font-style="{style.font_style}" '
        f'font-weight="{style.font_weight}" '
        f'font-size="{size_mm:.4f}" '
        f'fill="{fill}" text-anchor="start">'
    ]
    first_line_emitted = False
    for val in items:
        lines = r.wrap_lines(val, style, META_MAX_W_MM, hyphenate=True)
        for line in lines:
            dy = "0" if not first_line_emitted else f"{META_LEADING_MM:.4f}"
            parts.append(
                f'<tspan x="{META_X_MM}" dy="{dy}">{r.escape(line)}</tspan>'
            )
            first_line_emitted = True
    parts.append('</text>')
    return "".join(parts)
