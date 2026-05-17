"""Ficha — text side (right page of an artwork spread).

- Top cabecera + horizontal rule (shared with ficha_imagen).
- Long justified description body anchored to the top-left of row 2 /
  col 1 of the reticle, spanning the full reticle width.
- FUENTE / ESTADO footer line with bold labels and regular values.
- Folio strip at the bottom (shared).

Expected `data` keys:
    pieza_id (str)       — same as ficha_imagen
    cabecera_sub (str)   — same
    descripcion (str)    — multi-line body, auto-wraps + justified
    fuente (str)         — value after "FUENTE:" label
    estado (str)         — value after "ESTADO:" label
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


# Body: cap-top on the top line of reticle row 2, left edge on col 1,
# full reticle width. Style 24 is justified=True so the per-word
# justification path kicks in automatically.
_BODY_STYLE = TEXT_STYLES["24-Ficha-Descripcion"]
_BODY_CAP_HEIGHT_MM = _BODY_STYLE.size_pt * 0.685 * r.MM_PER_PT   # EB Garamond
BODY_X_MM = ch.LEFT_X_MM                                          # 15.4
BODY_Y_MM = ch.row_top(2) + _BODY_CAP_HEIGHT_MM
BODY_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM                          # 117.2

FOOTER_Y_MM = 183


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    cabecera_sub = str(data.get("cabecera_sub", "")).strip()
    descripcion = str(data.get("descripcion", "")).strip()
    fuente = str(data.get("fuente", "")).strip()
    estado = str(data.get("estado", "")).strip()

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top chrome
    parts.append(ch.cabecera(pieza_id, cabecera_sub))

    # — Justified description body
    if descripcion:
        parts.append(r.text(
            "24-Ficha-Descripcion", descripcion,
            x_mm=BODY_X_MM, y_mm=BODY_Y_MM,
            max_width_mm=BODY_W_MM,
        ))

    # — FUENTE / ESTADO line: bold labels, regular values
    if fuente or estado:
        parts.append(_meta_line(fuente, estado))

    # — Bottom chrome
    parts.append(r.folio(page_id))

    parts.append(r.svg_close())
    return "".join(parts)


def _meta_line(fuente: str, estado: str) -> str:
    """Render the FUENTE/ESTADO footer line.

    - Uses 26-Ficha-Fuente metrics (Lato 6.5pt tracking +50 gris).
    - Labels (FUENTE:, ESTADO:) render in font-weight 900; values in 400.
    - Wraps on word boundaries to fit the content width — InDesign re-flows
      anyway, but the preview should fit inside the margin.
    - `xml:space="preserve"` keeps the leading/trailing spaces inside tspans
      that some renderers (rsvg-convert, Safari) otherwise collapse.
    """
    from ..styles import TextStyle

    size_pt = 6.5
    size_mm = size_pt * r.MM_PER_PT
    leading_mm = 10 * r.MM_PER_PT          # 10pt leading per style 26
    ls_mm = (50 / 1000 * size_pt) * r.MM_PER_PT
    fill = r.PALETTE["gris_texto"]

    # Build the single-line source string, then wrap.
    segments: list[str] = []
    if fuente:
        segments.append(f"FUENTE: {fuente}")
    if estado:
        segments.append(f"ESTADO: {estado}")
    full = "  ·  ".join(segments)
    if not full:
        return ""

    wrap_style = TextStyle(
        font_family="Lato", size_pt=size_pt, tracking_per1000=50,
    )
    lines = r.wrap_lines(full, wrap_style, BODY_W_MM)

    # Emit each visual line as a <tspan x dy>, splitting bold labels inside.
    # Each weight gets its own font-family so the browser resolves the
    # correct Lato variant (Black for 900, Regular for 400) — see
    # render.font_family_css for why this matters on macOS.
    family_regular = r.font_family_css("Lato", 400)
    family_black = r.font_family_css("Lato", 900)

    line_tspans: list[str] = []
    for i, line in enumerate(lines):
        dy = "0" if i == 0 else f"{leading_mm:.4f}"
        bold_spans = "".join(
            f'<tspan font-family="{family_black if is_bold else family_regular}" '
            f'font-weight="{900 if is_bold else 400}">{text}</tspan>'
            for text, is_bold in _split_bold_labels(line)
        )
        line_tspans.append(
            f'<tspan x="{BODY_X_MM}" dy="{dy}">{bold_spans}</tspan>'
        )

    return (
        f'<text x="{BODY_X_MM}" y="{FOOTER_Y_MM}" '
        f'font-family="{family_regular}" '
        f'font-size="{size_mm:.4f}" '
        f'fill="{fill}" text-anchor="start" '
        f'letter-spacing="{ls_mm:.5f}" '
        f'xml:space="preserve">'
        f'{"".join(line_tspans)}</text>'
    )


def _split_bold_labels(line: str) -> list[tuple[str, bool]]:
    """Split a line into (text, is_bold) segments at FUENTE:/ESTADO: labels."""
    out: list[tuple[str, bool]] = []
    rest = line
    for label in ("FUENTE:", "ESTADO:"):
        idx = rest.find(label)
        if idx < 0:
            continue
        if idx > 0:
            out.append((rest[:idx], False))
        out.append((label, True))
        rest = rest[idx + len(label):]
    if rest:
        out.append((rest, False))
    return out or [(line, False)]
