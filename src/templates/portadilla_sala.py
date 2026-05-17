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


def render(page_id: int, data: dict) -> str:
    parts = [r.svg_open(r.PALETTE["rojo_tinta"])]

    # Roman numeral. Baseline near upper-third; slight indent past the margin
    # so the serifs of the "I" sit visually inside the column.
    romano = str(data.get("romano", "")).strip()
    if romano:
        parts.append(r.text(
            "13-Portadilla-Romano",
            romano,
            x_mm=r.MARGIN_MM + 14,
            y_mm=85,
        ))

    # Section title — Lato Black, wraps within content width if long.
    nombre = str(data.get("nombre", "")).strip()
    if nombre:
        parts.append(r.text(
            "14-Portadilla-Nombre",
            nombre,
            x_mm=r.MARGIN_MM,
            y_mm=108,
            max_width_mm=r.CONTENT_W_MM,
        ))

    # Metadata line: "<periodo>  ·  <piezas>" — both uppercased by the style.
    periodo = str(data.get("periodo", "")).strip()
    piezas = str(data.get("piezas", "")).strip()
    meta_segments = [s for s in (periodo, piezas) if s]
    if meta_segments:
        parts.append(r.text(
            "15-Portadilla-Periodo",
            "  ·  ".join(meta_segments),
            x_mm=r.MARGIN_MM,
            y_mm=118,
        ))

    # Curatorial quote — lower third, italic serif.
    quote = str(data.get("cita_curatorial", "")).strip()
    if quote:
        parts.append(r.text(
            "16-Portadilla-CitaCurato",
            quote,
            x_mm=r.MARGIN_MM,
            y_mm=160,
            max_width_mm=r.CONTENT_W_MM,
        ))

    # Folio (page number) — bottom-left, cream.
    parts.append(r.text(
        "Folio-Light",
        str(page_id),
        x_mm=r.MARGIN_MM,
        y_mm=r.TRIM_H_MM - 7,
    ))

    parts.append(r.svg_close())
    return "".join(parts)
