"""Índice — table-of-contents page on cream paper.

Layout:
- "Índice" big title (08-Seccion-Titulo, Lato Black 22pt) with its
  baseline anchored to the BOTTOM of cell (row 1, col 1).
- 6 sala rows from row 3 down (one sala per reticle row). Each row:
    - Roman numeral (10-Indice-Romano, Garamond 16pt rojo) at TOP-LEFT
      of cell (col 1) — cap-top on the row's top edge.
    - Sala name (11-Indice-Sala, Lato Black 11pt) at TOP-LEFT of cell
      (col 2) — same cap-top as the roman, so the row reads as one
      visual line even though baselines differ.
    - Page number (11-Indice-Sala, same style, anchor=end) at TOP-RIGHT
      of cell (col 6).
    - Date range (12-Indice-Periodo, Garamond italic 9pt gris), 4mm
      VISIBLE gap below the title's descender, left-anchored at col 2.

Expected `data` keys:
    titulo (str)            — defaults to "Índice"
    entradas (list[dict])   — each item: {romano, nombre, periodo, pagina}
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


# Style metric ratios (em fractions).
_LATO_CAP_RATIO = 0.72
_LATO_DESC_RATIO = 0.21
_GARAMOND_CAP_RATIO = 0.685

# Horizontal anchors.
TITLE_X_MM = ch.LEFT_X_MM                           # col 1 left
ROMANO_X_MM = ch.LEFT_X_MM                          # col 1 left
NOMBRE_X_MM = r.RETICLE_COL_RIGHT_X_MM[0] + r.RETICLE_GUTTER_MM  # col 2 left
PAGINA_X_MM = ch.RIGHT_X_MM                         # col 6 right (anchor=end)

# Section title fits between col 2 left and col 6 left (= cols 2..5) so it
# never overlaps the page number that sits in col 6.
NOMBRE_MAX_W_MM = r.RETICLE_COL_RIGHT_X_MM[4] - NOMBRE_X_MM   # col 2 left → col 5 right

# Title at bottom-left of cell (row 1, col 1): baseline at row_bottom(1).
_TITULO_STYLE = TEXT_STYLES["Indice-Titulo"]
TITULO_BASELINE_Y_MM = ch.row_bottom(1)

# Per-sala-row text positions, all derived from row_top(n).
_ROMANO_STYLE = TEXT_STYLES["10-Indice-Romano"]
_NOMBRE_STYLE = TEXT_STYLES["11-Indice-Sala"]
_PERIODO_STYLE = TEXT_STYLES["12-Indice-Periodo"]
_ROMANO_CAP_H_MM = _GARAMOND_CAP_RATIO * _ROMANO_STYLE.size_pt * r.MM_PER_PT
_NOMBRE_CAP_H_MM = _LATO_CAP_RATIO * _NOMBRE_STYLE.size_pt * r.MM_PER_PT
_NOMBRE_DESC_MM = _LATO_DESC_RATIO * _NOMBRE_STYLE.size_pt * r.MM_PER_PT
_PERIODO_CAP_H_MM = _GARAMOND_CAP_RATIO * _PERIODO_STYLE.size_pt * r.MM_PER_PT
_PERIODO_GAP_MM = 4.0   # 0.4 cm visible gap from título's descender

# First sala lives on row 3, then one sala per row.
_FIRST_SALA_ROW = 3


def render(page_id: int, data: dict) -> str:
    titulo = str(data.get("titulo", "Índice")).strip()
    entradas = data.get("entradas") or []

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    if titulo:
        parts.append(r.text(
            "Indice-Titulo", titulo,
            x_mm=TITLE_X_MM, y_mm=TITULO_BASELINE_Y_MM,
        ))

    for i, entry in enumerate(entradas):
        row = _FIRST_SALA_ROW + i
        row_top = ch.row_top(row)
        romano = str(entry.get("romano", "")).strip()
        nombre = str(entry.get("nombre", "")).strip()
        periodo = str(entry.get("periodo", "")).strip()
        pagina = entry.get("pagina")

        if romano:
            parts.append(r.text(
                "10-Indice-Romano", romano,
                x_mm=ROMANO_X_MM, y_mm=row_top + _ROMANO_CAP_H_MM,
            ))
        nombre_baseline = row_top + _NOMBRE_CAP_H_MM
        if nombre:
            parts.append(r.text(
                "11-Indice-Sala", nombre,
                x_mm=NOMBRE_X_MM, y_mm=nombre_baseline,
                max_width_mm=NOMBRE_MAX_W_MM,
            ))
        if pagina is not None:
            parts.append(r.text(
                "11-Indice-Sala", str(pagina),
                x_mm=PAGINA_X_MM, y_mm=nombre_baseline,
                align="end",
            ))
        if periodo:
            periodo_baseline = (
                nombre_baseline + _NOMBRE_DESC_MM + _PERIODO_GAP_MM + _PERIODO_CAP_H_MM
            )
            parts.append(r.text(
                "12-Indice-Periodo", periodo,
                x_mm=NOMBRE_X_MM, y_mm=periodo_baseline,
                align="start",
            ))

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)
