"""Nota curatorial — cream-paper essay pages.

The same template renders both the section's first page (label + title with
red rule + body) and continuation pages (body only).

Layout mirrors reference pages 3-4:
- Label (e.g. "NOTA CURATORIAL"), rojo_tinta, tracked uppercase, top-left.
- Red vertical rule + Lato Black title.
- Body in EB Garamond Regular 10/15.5, paragraphs split on blank lines.
- First paragraph flush left; every other paragraph gets a 5mm first-line
  indent. Continuation pages set `is_continuation: true` so their first
  paragraph is also indented (because it's the continuation of an essay,
  not the start of one).

Expected `data` keys:
    label (str, optional)            — e.g. "Nota curatorial"
    titulo (str, optional)           — section title; auto-wraps to 2 lines
    body (str)                       — paragraphs separated by blank lines
    is_continuation (bool, optional) — defaults to False
"""

from __future__ import annotations

from .. import render as r

# Geometry for the title block on the first page.
LABEL_Y_MM = 20
RULE_TOP_Y_MM = 28
RULE_H_MM = 20
TITLE_X_MM = r.MARGIN_MM + 6     # past the red rule + small gap
TITLE_Y_MM = 37
TITLE_MAX_W_MM = r.CONTENT_W_MM - 6

# Body starts higher on continuation pages (no header to clear).
BODY_TOP_Y_MM_WITH_HEADER = 75
BODY_TOP_Y_MM_CONTINUATION = 33

PARA_INDENT_MM = 5


def render(page_id: int, data: dict) -> str:
    label = str(data.get("label", "")).strip()
    titulo = str(data.get("titulo", "")).strip()
    body = str(data.get("body", "")).strip()
    is_continuation = bool(data.get("is_continuation", False))

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    has_header = bool(label or titulo)

    if label:
        parts.append(r.text("07-Seccion-Label", label,
                            x_mm=r.MARGIN_MM, y_mm=LABEL_Y_MM))
    if titulo:
        parts.append(r.red_rule_vertical(
            r.MARGIN_MM, RULE_TOP_Y_MM, RULE_H_MM,
        ))
        parts.append(r.text(
            "08-Seccion-Titulo", titulo,
            x_mm=TITLE_X_MM, y_mm=TITLE_Y_MM,
            max_width_mm=TITLE_MAX_W_MM,
        ))

    if body:
        y = BODY_TOP_Y_MM_WITH_HEADER if has_header else BODY_TOP_Y_MM_CONTINUATION
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs):
            # First para of a non-continuation page is flush; everything else
            # gets the first-line indent.
            indent = PARA_INDENT_MM if (is_continuation or i > 0) else 0
            svg, height_mm = r.paragraph(
                "09-Body-Garamond", para,
                x_mm=r.MARGIN_MM, y_mm=y,
                max_width_mm=r.CONTENT_W_MM,
                first_line_indent_mm=indent,
            )
            parts.append(svg)
            y += height_mm

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)
