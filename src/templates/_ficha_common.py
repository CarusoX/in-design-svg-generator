"""Shared chrome for ficha_imagen + ficha_texto.

Both pages of a ficha spread carry the same cabecera (ID + sala) at the top
and the same folio strip (page number + ID) at the bottom. Centralised here
so the two templates stay focused on their unique content.
"""

from __future__ import annotations

from .. import render as r

# Y positions of the chrome (mm from top of trim).
CABECERA_Y_MM = 18           # baseline of the top labels
CABECERA_RULE_Y_MM = 22      # horizontal rule under the cabecera
FOLIO_Y_MM = r.TRIM_H_MM - 7  # baseline of the bottom folio strip

# Right-side x for end-aligned text in the cabecera and folio.
RIGHT_X_MM = r.MARGIN_MM + r.CONTENT_W_MM  # 134


def cabecera(pieza_id: str, cabecera_sub: str) -> str:
    """Top-of-page chrome: ID (red, start) + sala/group (gray, end) + rule."""
    out: list[str] = []
    if pieza_id:
        out.append(r.text("17-Ficha-Cabecera-ID", pieza_id,
                          x_mm=r.MARGIN_MM, y_mm=CABECERA_Y_MM))
    if cabecera_sub:
        out.append(r.text("18-Ficha-Cabecera-Sub", cabecera_sub,
                          x_mm=RIGHT_X_MM, y_mm=CABECERA_Y_MM))
    out.append(r.ficha_header_rule(CABECERA_RULE_Y_MM))
    return "".join(out)


def folio(page_id: int, pieza_id: str) -> str:
    """Bottom-of-page chrome: page number (left) + ID (right)."""
    out = [
        r.text("Folio-Dark", str(page_id),
               x_mm=r.MARGIN_MM, y_mm=FOLIO_Y_MM),
    ]
    if pieza_id:
        out.append(r.text("18-Ficha-Cabecera-Sub", pieza_id,
                          x_mm=RIGHT_X_MM, y_mm=FOLIO_Y_MM))
    return "".join(out)
