"""Shared chrome for ficha_imagen + ficha_texto.

Both pages of a ficha spread carry the same cabecera (ID + sala) at the
top. Page-number folios go through `r.folio()` directly — no per-template
helper needed.
"""

from __future__ import annotations

from .. import render as r

# Y positions of the chrome (mm from top of trim).
# Header rule lands on the reticle's first horizontal line; labels sit
# above it with a 4mm gap (= one reticle gutter).
CABECERA_RULE_Y_MM = r.MARGIN_MM + r.RETICLE_INSET_MM   # 15.4
CABECERA_Y_MM = CABECERA_RULE_Y_MM - r.RETICLE_GUTTER_MM  # 11.4 (baseline above rule)

# Horizontal anchors aligned to the reticle's first and last vertical lines:
#   LEFT_X_MM  = first vline  = MARGIN + INSET
#   RIGHT_X_MM = last vline   = MARGIN + CONTENT_W - INSET
# Text labels start (left) / end (right) on these lines; the header rule
# spans exactly between them.
LEFT_X_MM = r.MARGIN_MM + r.RETICLE_INSET_MM                       # 15.4
RIGHT_X_MM = r.MARGIN_MM + r.CONTENT_W_MM - r.RETICLE_INSET_MM     # 132.6
RULE_LENGTH_MM = RIGHT_X_MM - LEFT_X_MM                            # 117.2


def cabecera(pieza_id: str, cabecera_sub: str) -> str:
    """Top-of-page chrome: ID (red, start) + sala/group (gray, end) + rule."""
    out: list[str] = []
    if pieza_id:
        out.append(r.text("17-Ficha-Cabecera-ID", pieza_id,
                          x_mm=LEFT_X_MM, y_mm=CABECERA_Y_MM))
    if cabecera_sub:
        out.append(r.text("18-Ficha-Cabecera-Sub", cabecera_sub,
                          x_mm=RIGHT_X_MM, y_mm=CABECERA_Y_MM))
    out.append(r.ficha_header_rule(
        CABECERA_RULE_Y_MM, x_mm=LEFT_X_MM, length_mm=RULE_LENGTH_MM,
    ))
    return "".join(out)
