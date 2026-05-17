"""Bibliografía — references list on cream paper.

Layout mirrors reference page 127:
- "BIBLIOGRAFÍA" label (rojo, tracked uppercase).
- "Referencias" title (Lato Black).
- A flat list of references, each rendered with a 5mm hanging indent
  (27-Biblio-Referencia style). Small vertical gap between entries.

Expected `data` keys:
    label (str)               — defaults to "Bibliografía"
    titulo (str)              — defaults to "Referencias"
    referencias (list[str])   — one reference per item (Author, Year, Title…)
"""

from __future__ import annotations

from .. import render as r

LABEL_Y_MM = 20
TITLE_Y_MM = 37
LIST_TOP_Y_MM = 62

# Gap between consecutive references (beyond the paragraph's own height).
ENTRY_GAP_MM = 2.0

HANGING_INDENT_MM = 5.0


def render(page_id: int, data: dict) -> str:
    label = str(data.get("label", "Bibliografía")).strip()
    titulo = str(data.get("titulo", "Referencias")).strip()
    referencias = [str(s).strip() for s in (data.get("referencias") or []) if str(s).strip()]

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    if label:
        parts.append(r.text("07-Seccion-Label", label,
                            x_mm=r.MARGIN_MM, y_mm=LABEL_Y_MM))
    if titulo:
        parts.append(r.text("08-Seccion-Titulo", titulo,
                            x_mm=r.MARGIN_MM, y_mm=TITLE_Y_MM,
                            max_width_mm=r.CONTENT_W_MM))

    y = LIST_TOP_Y_MM
    for ref in referencias:
        svg, height_mm = r.paragraph(
            "27-Biblio-Referencia", ref,
            x_mm=r.MARGIN_MM, y_mm=y,
            max_width_mm=r.CONTENT_W_MM,
            hanging_indent_mm=HANGING_INDENT_MM,
        )
        parts.append(svg)
        y += height_mm + ENTRY_GAP_MM

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)
