"""Créditos / colofón — page-2 imprint page.

White verso facing the epígrafe. Carries the book's identification
(title, subtitle, volume), an authorship/credits block, an academic
use-of-sources note, and the place/date line.

Layout (white background, left-aligned to the LEFT edge of reticle
column 3 — text occupies columns 3-6). Every block is anchored to a
fixed reticle row edge:

    Title        cap-top on the TOP of row 3
    Subtitle     last baseline on the BOTTOM of row 3
    Volumen      cap-top on the TOP of row 4
    Hairline     on the BOTTOM of row 4
    Credits      first cap-top on the TOP of row 5 (then flows down)
    Contexto     first cap-top on the TOP of row 6 (then flows down)
    Nota legal   first cap-top on the TOP of row 8 (then flows down)
    Lugar        baseline on the BOTTOM of row 9

Expected `data` keys (all optional; whatever's present renders):
    titulo (str)      — book title
    subtitulo (str)   — descriptive subtitle (wraps)
    volumen (str)     — volume + date-range line
    creditos (list)   — authorship lines, anchored to row 5 (each wraps)
    contexto (list)   — academic-context block (course / professor /
                        typefaces), anchored to row 6 (each wraps)
    nota_legal (str)  — academic / source-use note (wraps)
    lugar (str)       — place + year (anchored to the foot of the page)
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch

_GARAMOND_CAP_RATIO = 0.685
_LATO_CAP_RATIO = 0.72

# Left edge of reticle column 3 = right edge of column 2 + one gutter.
# (RETICLE_COL_RIGHT_X_MM[i] is the right edge of column i+1.)
LEFT_X_MM = r.RETICLE_COL_RIGHT_X_MM[1] + r.RETICLE_GUTTER_MM
RIGHT_X_MM = ch.RIGHT_X_MM
WIDTH_MM = RIGHT_X_MM - LEFT_X_MM

# Gap between successive credit lines (descender-to-cap-top breathing room).
_CREDIT_GAP_MM = 1.0


def _cap_h_mm(style) -> float:
    """Cap height (mm) for the style's font — used to seat a line's
    cap-top on a reticle row's TOP edge."""
    ratio = _LATO_CAP_RATIO if style.font_family == "Lato" else _GARAMOND_CAP_RATIO
    return ratio * style.size_pt * r.MM_PER_PT


def _leading_mm(style) -> float:
    return (style.leading_pt or style.size_pt * 1.2) * r.MM_PER_PT


def _emit_flowing_lines(parts: list[str], lines, style_id: str, first_baseline_y: float) -> float:
    """Render a list of text lines (each wrapping independently) with the
    first line's baseline at `first_baseline_y`, flowing downward. Returns
    the baseline where the next line would start."""
    y = first_baseline_y
    for line in lines:
        line = str(line).strip()
        if not line:
            continue
        svg, h = r.paragraph(style_id, line, LEFT_X_MM, y, WIDTH_MM)
        parts.append(svg)
        y += h + _CREDIT_GAP_MM
    return y


def render(page_id: int, data: dict) -> str:
    titulo = str(data.get("titulo", "")).strip()
    subtitulo = str(data.get("subtitulo", "")).strip()
    volumen = str(data.get("volumen", "")).strip()
    creditos = data.get("creditos") or []
    contexto = data.get("contexto") or []
    nota_legal = str(data.get("nota_legal", "")).strip()
    lugar = str(data.get("lugar", "")).strip()

    parts = [r.svg_open(r.PALETTE["blanco"])]

    # — Title: cap-top on the TOP of row 3.
    if titulo:
        st = TEXT_STYLES["Creditos-Titulo"]
        svg, _ = r.paragraph(
            "Creditos-Titulo", titulo,
            LEFT_X_MM, ch.row_top(3) + _cap_h_mm(st), WIDTH_MM,
        )
        parts.append(svg)

    # — Subtitle: LAST baseline on the BOTTOM of row 3 (stacks upward by
    # measuring its line count first).
    if subtitulo:
        st = TEXT_STYLES["Creditos-Subtitulo"]
        lead = _leading_mm(st)
        _, h = r.paragraph("Creditos-Subtitulo", subtitulo, LEFT_X_MM, 0.0, WIDTH_MM)
        n = max(1, round(h / lead))
        first_baseline = ch.row_bottom(3) - (n - 1) * lead
        svg, _ = r.paragraph(
            "Creditos-Subtitulo", subtitulo, LEFT_X_MM, first_baseline, WIDTH_MM,
        )
        parts.append(svg)

    # — Volumen / fecha: cap-top on the TOP of row 4.
    if volumen:
        st = TEXT_STYLES["Creditos-Volumen"]
        svg, _ = r.paragraph(
            "Creditos-Volumen", volumen,
            LEFT_X_MM, ch.row_top(4) + _cap_h_mm(st), WIDTH_MM,
        )
        parts.append(svg)

    # — Hairline red rule: on the BOTTOM of row 4.
    parts.append(r.ficha_footer_rule(ch.row_bottom(4), x_mm=LEFT_X_MM, length_mm=WIDTH_MM))

    # — Authorship credits: first cap-top on the TOP of row 5, flow down.
    st = TEXT_STYLES["Creditos-Linea"]
    if creditos:
        _emit_flowing_lines(parts, creditos, "Creditos-Linea", ch.row_top(5) + _cap_h_mm(st))

    # — Academic-context block: first cap-top on the TOP of row 6, flow down.
    if contexto:
        _emit_flowing_lines(parts, contexto, "Creditos-Linea", ch.row_top(6) + _cap_h_mm(st))

    # — Use-of-sources note: first cap-top on the TOP of row 8, then flow down.
    if nota_legal:
        st = TEXT_STYLES["Creditos-Nota"]
        svg, _ = r.paragraph(
            "Creditos-Nota", nota_legal,
            LEFT_X_MM, ch.row_top(8) + _cap_h_mm(st), WIDTH_MM,
        )
        parts.append(svg)

    # — Place + year: baseline on the BOTTOM of row 9 (foot of the page).
    if lugar:
        parts.append(r.text(
            "Creditos-Lugar", lugar,
            x_mm=LEFT_X_MM, y_mm=ch.row_bottom(9),
        ))

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)
