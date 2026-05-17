"""Ficha — text side (right page of an artwork spread).

- Top cabecera + horizontal rule (shared with ficha_imagen).
- Long left-aligned description body anchored to the top-left of row 2 /
  col 1 of the reticle, spanning the full reticle width.
- Folio strip at the bottom (shared).

Expected `data` keys:
    pieza_id (str)       — same as ficha_imagen
    cabecera_sub (str)   — same
    descripcion (str)    — multi-line body, auto-wraps + hyphenates
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


# Body: cap-top on the top line of reticle row 2, left edge on col 1,
# full reticle width.
_BODY_STYLE = TEXT_STYLES["24-Ficha-Descripcion"]
_BODY_CAP_HEIGHT_MM = _BODY_STYLE.size_pt * 0.685 * r.MM_PER_PT   # EB Garamond
BODY_X_MM = ch.LEFT_X_MM                                          # 15.4
BODY_Y_MM = ch.row_top(2) + _BODY_CAP_HEIGHT_MM
BODY_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM                          # 117.2


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    cabecera_sub = str(data.get("cabecera_sub", "")).strip()
    descripcion = str(data.get("descripcion", "")).strip()

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top chrome
    parts.append(ch.cabecera(pieza_id, cabecera_sub))

    # — Description body (left-aligned, hyphenated wrap)
    if descripcion:
        parts.append(r.text(
            "24-Ficha-Descripcion", descripcion,
            x_mm=BODY_X_MM, y_mm=BODY_Y_MM,
            max_width_mm=BODY_W_MM,
        ))

    # — Bottom chrome
    parts.append(r.folio(page_id))

    parts.append(r.svg_close())
    return "".join(parts)
