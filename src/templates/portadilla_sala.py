"""Portadilla de sala — full-bleed red section title page.

Layout mirrors reference page 6:
- Background: rojo_tinta full bleed.
- Roman numeral: large EB Garamond, upper-third, cream.
- Section title: Lato Black, cream, just below the numeral.
- Metadata line "<periodo>  ·  <piezas>": uppercase, tracked Lato Black.
- Curatorial quote: italic serif (EB Garamond Italic) in the lower third.
- Page folio: small Lato in cream, bottom-left.

Expected `data` keys:
    romano (str)            — Roman numeral, e.g. "I"
    nombre (str)            — section title
    periodo (str, optional) — e.g. "Pre-1764"
    piezas (str|int, opt.)  — e.g. "2 piezas" (the template uppercases)
    cita_curatorial (str)   — quote text; may contain explicit "\\n" breaks
"""

from __future__ import annotations

from .. import render as r


# Positions taken from tests/ground-truth/Section1.svg (Illustrator export
# by the design teammate). Values converted from points → mm via × 0.3528.
ROMAN_X_MM = 14.31
ROMAN_Y_MM = 72.06
TITLE_X_MM = 15.41
TITLE_Y_MM = 102.37
META_Y_MM = 113.10
QUOTE_Y_MM = 161.26
FOLIO_X_MM = 13.65
FOLIO_Y_MM = 203.04

# Text columns end at the reticle's right edge (= MARGIN + CONTENT - INSET).
# Cap the wrapping at this so justified lines don't overflow past the grid.
TEXT_MAX_W_MM = (r.MARGIN_MM + r.CONTENT_W_MM - r.RETICLE_INSET_MM) - TITLE_X_MM


def render(page_id: int, data: dict) -> str:
    parts = [r.svg_open(r.PALETTE["rojo_tinta"])]

    # Roman numeral. Baseline near upper-third.
    romano = str(data.get("romano", "")).strip()
    if romano:
        parts.append(r.text(
            "13-Portadilla-Romano",
            romano,
            x_mm=ROMAN_X_MM,
            y_mm=ROMAN_Y_MM,
        ))

    # Section title — Lato Black, wraps within content width if long.
    nombre = str(data.get("nombre", "")).strip()
    if nombre:
        parts.append(r.text(
            "14-Portadilla-Nombre",
            nombre,
            x_mm=TITLE_X_MM,
            y_mm=TITLE_Y_MM,
            max_width_mm=TEXT_MAX_W_MM,
        ))

    # Metadata line: "<periodo>  ·  <piezas>" — both uppercased by the style.
    periodo = str(data.get("periodo", "")).strip()
    piezas = str(data.get("piezas", "")).strip()
    meta_segments = [s for s in (periodo, piezas) if s]
    if meta_segments:
        parts.append(r.text(
            "15-Portadilla-Periodo",
            "  ·  ".join(meta_segments),
            x_mm=TITLE_X_MM,
            y_mm=META_Y_MM,
        ))

    # Curatorial quote — lower third, italic serif.
    quote = str(data.get("cita_curatorial", "")).strip()
    if quote:
        parts.append(r.text(
            "16-Portadilla-CitaCurato",
            quote,
            x_mm=TITLE_X_MM,
            y_mm=QUOTE_Y_MM,
            max_width_mm=TEXT_MAX_W_MM,
        ))

    # Folio (page number) — bottom-left, cream.
    parts.append(r.text(
        "Folio-Light",
        str(page_id),
        x_mm=FOLIO_X_MM,
        y_mm=FOLIO_Y_MM,
    ))

    parts.append(r.svg_close())
    return "".join(parts)
