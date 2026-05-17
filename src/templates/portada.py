"""Portada — cover page on full-bleed rojo_tinta.

- No top label (volumen / rango removed at user's request).
- Mid-page: 3-line title (Lato Black) + italic serif subtitle, both in
  papel_crema for contrast against the red field.
- Bottom label: "X PIEZAS  ·  N SALAS" in tracked Lato Black caps.
- No folio.

Expected `data` keys:
    titulo (str)     — title with explicit "\\n" for editorial line breaks
    subtitulo (str)  — italic serif subtitle (auto-wraps)
    piezas (str|int) — e.g. "57 piezas" (uppercased by style)
    salas (str|int)  — e.g. "7 salas"
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


_LATO_CAP_RATIO = 0.72

# Reticle-anchored geometry:
#   - Hairline rule sits flush against the RIGHT edge of column 1,
#     starting at the TOP of row 3.
#   - Title baseline lands so its cap-top sits on the TOP of row 3
#     (same row as the rule), starting at the LEFT edge of column 2.
_COL_1_RIGHT_X_MM = r.RETICLE_COL_RIGHT_X_MM[0]
_COL_2_LEFT_X_MM = _COL_1_RIGHT_X_MM + r.RETICLE_GUTTER_MM
_ROW_3_TOP_Y_MM = ch.row_top(3)

RULE_W_MM = 0.5          # thin cream hairline on the red field
RULE_X_MM = _COL_1_RIGHT_X_MM - RULE_W_MM   # rule's right edge on col 1 right
RULE_Y_MM = _ROW_3_TOP_Y_MM
RULE_H_MM = 60

_TITLE_STYLE = TEXT_STYLES["02-Portada-Titulo"]
_TITLE_CAP_H_MM = _LATO_CAP_RATIO * _TITLE_STYLE.size_pt * r.MM_PER_PT
_TITLE_LEADING_MM = (
    (_TITLE_STYLE.leading_pt or _TITLE_STYLE.size_pt * 1.2) * r.MM_PER_PT
)
TITLE_X_MM = _COL_2_LEFT_X_MM
# Title's LAST line baseline sits on the bottom edge of row 5; previous
# lines stack UPWARD by one leading each. Cómodo para títulos cortos de
# 2-3 líneas (la actual es 3: "Archivo / de lo no / conservado").
TITLE_LAST_BASELINE_Y_MM = ch.row_bottom(5)

# Subtítulo y label inferior — ambos anclados a la columna 2; baseline
# en el borde inferior de su fila (fila 7 y fila 8 respectivamente).
SUBTITULO_X_MM = _COL_2_LEFT_X_MM
SUBTITULO_BASELINE_Y_MM = ch.row_bottom(7)
BOTTOM_LABEL_X_MM = _COL_2_LEFT_X_MM
BOTTOM_LABEL_BASELINE_Y_MM = ch.row_bottom(8)


def render(page_id: int, data: dict) -> str:
    parts = [r.svg_open(r.PALETTE["rojo_tinta"])]

    # — Vertical hairline next to the title, in papel_crema on the
    # rojo_tinta background.
    parts.append(
        f'<rect x="{RULE_X_MM}" y="{RULE_Y_MM}" '
        f'width="{RULE_W_MM}" height="{RULE_H_MM}" '
        f'fill="{r.PALETTE["papel_crema"]}"/>'
    )

    # — Title (manual line breaks via "\n" in YAML). LAST line baseline
    # at row_bottom(5); earlier lines stack upward by one leading each,
    # so the title's bottom always lands on the same reticle line
    # regardless of how many lines the YAML specifies.
    title_max_w_mm = ch.RIGHT_X_MM - TITLE_X_MM
    titulo = str(data.get("titulo", "")).strip()
    if titulo:
        n_lines = len(titulo.split("\n"))
        first_baseline_y_mm = (
            TITLE_LAST_BASELINE_Y_MM - (n_lines - 1) * _TITLE_LEADING_MM
        )
        parts.append(r.text(
            "02-Portada-Titulo",
            titulo,
            x_mm=TITLE_X_MM,
            y_mm=first_baseline_y_mm,
            max_width_mm=title_max_w_mm,
        ))

    # — Subtitle (italic serif, cream, auto-wraps). Baseline anclada al
    # borde inferior de fila 7.
    subtitulo = str(data.get("subtitulo", "")).strip()
    if subtitulo:
        parts.append(r.text(
            "03-Portada-Subtitulo",
            subtitulo,
            x_mm=SUBTITULO_X_MM,
            y_mm=SUBTITULO_BASELINE_Y_MM,
            max_width_mm=ch.RIGHT_X_MM - SUBTITULO_X_MM,
        ))

    # — Bottom label ("N PIEZAS  ·  M SALAS"). Baseline anclada al
    # borde inferior de fila 8.
    piezas = str(data.get("piezas", "")).strip()
    salas = str(data.get("salas", "")).strip()
    bottom_segments = [s for s in (piezas, salas) if s]
    if bottom_segments:
        parts.append(r.text(
            "01-Portada-Label",
            "  ·  ".join(bottom_segments),
            x_mm=BOTTOM_LABEL_X_MM,
            y_mm=BOTTOM_LABEL_BASELINE_Y_MM,
        ))

    parts.append(r.svg_close())
    return "".join(parts)
