"""Portada — cover page on a white field.

Three-part stacked title, all uppercase, anchored to the reticle:
  - Line 1 ("ARCHIVO"):  font-size fitted so the word spans the 4 central
                         columns (cols 2-5); baseline on the BOTTOM of row 3.
  - Line 2 ("DE LO NO"): fitted to span the 2 central columns (cols 3-4),
                         centered under the title and vertically centered in
                         row 4 (equal gap to the words above and below).
  - Line 3 ("CONSERVADO"): font-size fitted to span cols 2-5; cap-top on
                         the TOP of row 5.
Title parts come from the `titulo` field, split on newlines and
uppercased (the cover expects exactly three lines).

Below the title: italic serif subtitle (baseline on row 7 bottom) and the
"N PIEZAS · M SALAS" label (row 8 bottom). No vertical rule, no folio.

Expected `data` keys:
    titulo (str)     — three newline-separated parts (upper-cased here)
    subtitulo (str)  — italic serif subtitle (auto-wraps)
    piezas (str|int) — e.g. "78 piezas" (uppercased by style)
    salas (str|int)  — e.g. "12 salas"
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch

_LATO_CAP_RATIO = 0.72

# Title block: the 4 central columns (cols 2-5), same span as the epígrafe.
BLOCK_X0_MM = r.RETICLE_COL_RIGHT_X_MM[0] + r.RETICLE_GUTTER_MM   # col 2 left
BLOCK_X1_MM = r.RETICLE_COL_RIGHT_X_MM[4]                          # col 5 right
BLOCK_W_MM = BLOCK_X1_MM - BLOCK_X0_MM
BLOCK_CENTER_X_MM = BLOCK_X0_MM + BLOCK_W_MM / 2

# "DE LO NO" fills exactly the 2 central columns (cols 3-4).
MID2_X0_MM = r.RETICLE_COL_RIGHT_X_MM[1] + r.RETICLE_GUTTER_MM    # col 3 left
MID2_X1_MM = r.RETICLE_COL_RIGHT_X_MM[3]                          # col 4 right
MID2_W_MM = MID2_X1_MM - MID2_X0_MM

_TITLE_STYLE = TEXT_STYLES["02-Portada-Titulo"]   # Lato Bold, negro_tinta

# Authors, subtitle and bottom label are all centered on the page (= reticle
# center, x = BLOCK_CENTER_X_MM). The subtitle wraps across the full 6-column
# width.
_GARAMOND_CAP_RATIO = 0.685
FULL_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM
SUBTITULO_X_MM = BLOCK_CENTER_X_MM
# First line's cap-top on the TOP of row 7.
SUBTITULO_BASELINE_Y_MM = (
    ch.row_top(7)
    + _GARAMOND_CAP_RATIO * TEXT_STYLES["03-Portada-Subtitulo"].size_pt * r.MM_PER_PT
)
BOTTOM_LABEL_X_MM = BLOCK_CENTER_X_MM
BOTTOM_LABEL_BASELINE_Y_MM = ch.row_bottom(8)

# Authors: small tracked caps (the cover "label" style), centered, with the
# first line's cap-top on the TOP of row 1.
AUTORES_X_MM = BLOCK_CENTER_X_MM
_AUTORES_STYLE = TEXT_STYLES["Portada-Autores"]
AUTORES_FIRST_BASELINE_Y_MM = (
    ch.row_top(1) + _LATO_CAP_RATIO * _AUTORES_STYLE.size_pt * r.MM_PER_PT
)


# Average advance width per character for bold sans-serif UPPERCASE, as a
# fraction of em (Lato ≈ Arial/Helvetica bold caps: 0.66-0.71). The Pillow
# `char_factor` (0.46) is tuned for mixed-case body text and badly
# under-estimates caps, so it's not usable for the cover. We size the word
# from this constant to get the cap-height right, then pin the exact width
# with SVG `textLength` (below), which makes the column fit metric-independent.
_CAPS_ADV_FACTOR = 0.68
_SPACE_ADV_FACTOR = 0.30   # advance of a space, fraction of em


def _fit_size_pt(word: str, target_w_mm: float) -> float:
    """Font size (pt) whose natural uppercase width is ~`target_w_mm`. The
    exact fit is enforced by `textLength` at emit time; this just gets the
    cap-height into the right range so `textLength` barely has to stretch.
    Spaces are counted with a smaller advance than letters."""
    letters = len(word.replace(" ", ""))
    spaces = word.count(" ")
    units = max(
        _CAPS_ADV_FACTOR,
        letters * _CAPS_ADV_FACTOR + spaces * _SPACE_ADV_FACTOR,
    )
    return target_w_mm / (units * r.MM_PER_PT)


def _emit_title_word(
    word: str, size_pt: float, x_mm: float, baseline_y_mm: float,
    fill_w_mm: float | None = None, anchor: str = "start",
) -> str:
    """A single uppercase title word as <text> at the given size, baseline
    and text-anchor. When `fill_w_mm` is set, `textLength` +
    `lengthAdjust="spacingAndGlyphs"` force the word to span exactly that
    width (so it fills the columns regardless of font metrics)."""
    fill = r.PALETTE[_TITLE_STYLE.color]
    size_mm = size_pt * r.MM_PER_PT
    fam = r.font_family_css(_TITLE_STYLE.font_family, _TITLE_STYLE.font_weight)
    fit = (
        f' textLength="{fill_w_mm:.4f}" lengthAdjust="spacingAndGlyphs"'
        if fill_w_mm else ""
    )
    return (
        f'<text x="{x_mm:.4f}" y="{baseline_y_mm:.4f}" '
        f'font-family="{fam}" font-size="{size_mm:.4f}" '
        f'font-weight="{_TITLE_STYLE.font_weight}" fill="{fill}" '
        f'text-anchor="{anchor}"{fit}>{escape(word)}</text>'
    )


def render(page_id: int, data: dict) -> str:
    parts = [r.svg_open(r.PALETTE["blanco"])]

    # — Authors: two centered tracked-caps lines, first cap-top on row 1 top.
    autores = data.get("autores") or []
    if autores:
        parts.append(r.text(
            "Portada-Autores",
            [str(a).strip() for a in autores],
            x_mm=AUTORES_X_MM, y_mm=AUTORES_FIRST_BASELINE_Y_MM,
            align="middle",
        ))

    # — Three-part uppercase title (from `titulo`, split on newlines).
    titulo = str(data.get("titulo", "")).strip()
    lines = [ln.strip().upper() for ln in titulo.split("\n") if ln.strip()]
    top = lines[0] if len(lines) > 0 else ""
    middle = lines[1] if len(lines) > 1 else ""
    bottom = lines[2] if len(lines) > 2 else ""

    if top:
        size_top = _fit_size_pt(top, BLOCK_W_MM)
        # ARCHIVO: fills cols 2-5, baseline on the bottom of row 3.
        parts.append(_emit_title_word(
            top, size_top, BLOCK_X0_MM, ch.row_bottom(3), fill_w_mm=BLOCK_W_MM,
        ))
        # DE LO NO: smaller, horizontally centered under ARCHIVO and
        # vertically centered in row 4. Centering its cap-box on the row-4
        # midpoint puts equal vertical gap to ARCHIVO (above) and CONSERVADO
        # (below), since those sit on row 3 bottom and row 5 top.
        if middle:
            # DE LO NO fills exactly the 2 central columns (cols 3-4).
            size_mid = _fit_size_pt(middle, MID2_W_MM)
            mid_cap_h = _LATO_CAP_RATIO * size_mid * r.MM_PER_PT
            row4_center = (ch.row_top(4) + ch.row_bottom(4)) / 2
            parts.append(_emit_title_word(
                middle, size_mid, BLOCK_CENTER_X_MM,
                row4_center + mid_cap_h / 2, fill_w_mm=MID2_W_MM, anchor="middle",
            ))
    if bottom:
        size_bottom = _fit_size_pt(bottom, BLOCK_W_MM)
        cap_h = _LATO_CAP_RATIO * size_bottom * r.MM_PER_PT
        # CONSERVADO: fills cols 2-5, cap-top on the top of row 5.
        parts.append(_emit_title_word(
            bottom, size_bottom, BLOCK_X0_MM, ch.row_top(5) + cap_h,
            fill_w_mm=BLOCK_W_MM,
        ))

    # — Subtitle (italic serif, auto-wraps). Baseline on the bottom of row 7.
    subtitulo = str(data.get("subtitulo", "")).strip()
    if subtitulo:
        parts.append(r.text(
            "03-Portada-Subtitulo", subtitulo,
            x_mm=SUBTITULO_X_MM, y_mm=SUBTITULO_BASELINE_Y_MM,
            max_width_mm=FULL_W_MM, align="middle",
        ))

    # — Bottom label ("N PIEZAS  ·  M SALAS"). Baseline on the bottom of row 8.
    piezas = str(data.get("piezas", "")).strip()
    salas = str(data.get("salas", "")).strip()
    bottom_segments = [s for s in (piezas, salas) if s]
    if bottom_segments:
        parts.append(r.text(
            "01-Portada-Label", "  ·  ".join(bottom_segments),
            x_mm=BOTTOM_LABEL_X_MM, y_mm=BOTTOM_LABEL_BASELINE_Y_MM,
            align="middle",
        ))

    parts.append(r.svg_close())
    return "".join(parts)
