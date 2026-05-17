"""Epígrafe — full-bleed red page with a centred label, a large italic
serif quote, and a centred source line.

Layout mirrors reference page 2:
- Background: rojo_tinta.
- Label "EPÍGRAFE" centred horizontally near the upper third.
- Quote (italic serif, large, cream) left-aligned starting just below.
- Source line (italic serif, small, cream) centred below the quote.
- Folio in the outer margin (cream on red).

Expected `data` keys:
    label (str)   — defaults to "Epígrafe" (uppercased by the style)
    cita (str)    — main quote; auto-wraps to content width
    fuente (str)  — source line; supports explicit "\\n" for multi-line
"""

from __future__ import annotations

from .. import render as r

LABEL_Y_MM = 85
QUOTE_Y_MM = 100
SOURCE_Y_MM = 148

CENTER_X_MM = r.TRIM_W_MM / 2


def render(page_id: int, data: dict) -> str:
    label = str(data.get("label", "Epígrafe")).strip()
    cita = str(data.get("cita", "")).strip()
    fuente = str(data.get("fuente", "")).strip()

    parts = [r.svg_open(r.PALETTE["rojo_tinta"])]

    if label:
        parts.append(r.text("04-Epigrafe-Label", label,
                            x_mm=CENTER_X_MM, y_mm=LABEL_Y_MM))

    if cita:
        # Style 05 is align="middle" — anchor at page horizontal center.
        parts.append(r.text(
            "05-Epigrafe-Cita", cita,
            x_mm=CENTER_X_MM, y_mm=QUOTE_Y_MM,
            max_width_mm=r.CONTENT_W_MM,
        ))

    if fuente:
        parts.append(r.text(
            "06-Epigrafe-Fuente", fuente,
            x_mm=CENTER_X_MM, y_mm=SOURCE_Y_MM,
            max_width_mm=r.CONTENT_W_MM,
        ))

    parts.append(r.folio(page_id, light=True))

    parts.append(r.svg_close())
    return "".join(parts)
