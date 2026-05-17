"""Epígrafe — full-bleed rojo_tinta page with the quote centered in
the middle of the reticle, and the source line anchored to the bottom
of row 7.

Layout:
- Background: rojo_tinta.
- No label.
- Cita: 05-Epigrafe-Cita (EB Garamond regular weight 500, 22pt,
  centered on the page horizontally). Wraps within the middle 4-col
  width (cols 2-5). First line's cap-top sits on the TOP of row 4;
  subsequent lines stack down.
- Fuente: 06-Epigrafe-Fuente (small centered italic Garamond). Last
  line's baseline anchored to the bottom edge of row 7; multi-line
  source stacks upward from there.
- Light folio in the outer margin.

Expected `data` keys:
    cita (str)    — main quote; auto-wraps to box width
    fuente (str)  — source line; supports explicit "\\n" for multi-line
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


# Cita box width: cols 2-5 (middle 4 cols of the 6-col reticle).
_COL_2_LEFT = r.RETICLE_COL_RIGHT_X_MM[0] + r.RETICLE_GUTTER_MM
_COL_5_RIGHT = r.RETICLE_COL_RIGHT_X_MM[4]
BOX_W_MM = _COL_5_RIGHT - _COL_2_LEFT
BOX_CENTER_X_MM = (_COL_2_LEFT + _COL_5_RIGHT) / 2

# Author block: last baseline rides the bottom of row 7.
FUENTE_LAST_BASELINE_Y_MM = ch.row_bottom(7)

_CITA_STYLE = TEXT_STYLES["05-Epigrafe-Cita"]
_CITA_CAP_H_MM = 0.685 * _CITA_STYLE.size_pt * r.MM_PER_PT

_FUENTE_STYLE = TEXT_STYLES["06-Epigrafe-Fuente"]
_FUENTE_LEADING_MM = (
    (_FUENTE_STYLE.leading_pt or _FUENTE_STYLE.size_pt * 1.2) * r.MM_PER_PT
)


def render(page_id: int, data: dict) -> str:
    cita = str(data.get("cita", "")).strip()
    fuente = str(data.get("fuente", "")).strip()

    parts = [r.svg_open(r.PALETTE["rojo_tinta"])]

    if cita:
        # First line's cap-top sits at the top of row 4 (= baseline at
        # row_top(4) + cap_h). Subsequent lines stack downward. Never
        # hyphenate — display quote, mid-word breaks look bad.
        parts.append(r.text(
            "05-Epigrafe-Cita", cita,
            x_mm=BOX_CENTER_X_MM, y_mm=ch.row_top(4) + _CITA_CAP_H_MM,
            max_width_mm=BOX_W_MM,
            hyphenate=False,
        ))

    if fuente:
        # Fuente lines come from the YAML literal scalar (split on \n).
        fuente_lines = fuente.split("\n")
        first_baseline = (
            FUENTE_LAST_BASELINE_Y_MM - (len(fuente_lines) - 1) * _FUENTE_LEADING_MM
        )
        parts.append(r.text(
            "06-Epigrafe-Fuente", fuente_lines,
            x_mm=r.TRIM_W_MM / 2, y_mm=first_baseline,
        ))

    parts.append(r.folio(page_id, light=True))
    parts.append(r.svg_close())
    return "".join(parts)
