"""Índice — table-of-contents page on cream paper.

Layout mirrors reference page 5:
- "ÍNDICE" label (rojo, tracked uppercase).
- "Las siete salas" title (Lato Black).
- 7 rows, each: Roman numeral (rojo) | sala name (Lato Black) | period
  (Garamond Italic, gris, right-aligned).

Expected `data` keys:
    label (str)             — defaults to "Índice"
    titulo (str)            — section heading
    entradas (list[dict])   — each item: {romano, nombre, periodo}
"""

from __future__ import annotations

from .. import render as r

LABEL_Y_MM = 20
TITLE_Y_MM = 37

# Row layout.
ROW_START_Y_MM = 80
ROW_SPACING_MM = 18

# Column positions (mm from left).
ROMANO_X_MM = r.MARGIN_MM            # 14 — left-anchored Roman
NOMBRE_X_MM = r.MARGIN_MM + 28       # 42 — past the widest Roman ("VII")
PERIODO_X_MM = r.MARGIN_MM + r.CONTENT_W_MM   # 134 — right-anchored


def render(page_id: int, data: dict) -> str:
    label = str(data.get("label", "Índice")).strip()
    titulo = str(data.get("titulo", "")).strip()
    entradas = data.get("entradas") or []

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    if label:
        parts.append(r.text("07-Seccion-Label", label,
                            x_mm=r.MARGIN_MM, y_mm=LABEL_Y_MM))
    if titulo:
        parts.append(r.text("08-Seccion-Titulo", titulo,
                            x_mm=r.MARGIN_MM, y_mm=TITLE_Y_MM,
                            max_width_mm=r.CONTENT_W_MM))

    for i, entry in enumerate(entradas):
        romano = str(entry.get("romano", "")).strip()
        nombre = str(entry.get("nombre", "")).strip()
        periodo = str(entry.get("periodo", "")).strip()
        y = ROW_START_Y_MM + i * ROW_SPACING_MM

        if romano:
            parts.append(r.text("10-Indice-Romano", romano,
                                x_mm=ROMANO_X_MM, y_mm=y))
        if nombre:
            parts.append(r.text("11-Indice-Sala", nombre,
                                x_mm=NOMBRE_X_MM, y_mm=y,
                                max_width_mm=PERIODO_X_MM - NOMBRE_X_MM - 4))
        if periodo:
            parts.append(r.text("12-Indice-Periodo", periodo,
                                x_mm=PERIODO_X_MM, y_mm=y))

    parts.append(r.text(
        "Folio-Dark", str(page_id),
        x_mm=r.MARGIN_MM, y_mm=r.TRIM_H_MM - 7,
    ))
    parts.append(r.svg_close())
    return "".join(parts)
