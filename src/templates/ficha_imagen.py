"""Ficha — image side (left page of an artwork spread).

- Top cabecera + horizontal rule (shared with ficha_texto).
- Red vertical rule + tipo (red italic eyebrow) + Lato Black title.
  autor / datos / estado live on the text page now.
- Large image placeholder frame (or real image when provided).
  Frame carries small internal labels: ID top-left, "categoría X"
  bottom-right, centered "imagen disponible…" hint.
- Caption (italic gray) below the frame, left-aligned in cols 1–6.
- Folio strip at the bottom (shared).

Expected `data` keys:
    pieza_id (str)       — e.g. "L001"
    cabecera_sub (str)   — e.g. "Orígenes y sustratos prehispánicos (Pre-1764)"
    tipo (str)           — italic serif eyebrow, red
    titulo (str)         — artwork title (auto-wraps to 2 lines if needed)
    image (str, opt.)    — relative path to the placed image; when absent,
                            the placeholder frame is drawn
    categoria (str)      — e.g. "A", "B" (defaults to "A")
    caption (str)        — caption text below the image
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


# Reticle row math comes from ch (shared). Cached aliases for the rows
# that matter on this page.
_RETICLE_LEFT_X_MM = ch.LEFT_X_MM                            # 15.4
_RETICLE_RIGHT_X_MM = ch.RIGHT_X_MM                          # 132.6
_ROW_1_BOTTOM_Y = ch.row_bottom(1)
_ROW_2_TOP_Y = ch.row_top(2)
_ROW_2_BOTTOM_Y = ch.row_bottom(2)

# Horizontal positions for the tipo/title block:
#   - Red rule left edge sits on the first vertical reticle line.
#   - Text starts one reticle gutter (4mm) past the rule's right edge.
RULE_X_MM = r.MARGIN_MM + r.RETICLE_INSET_MM      # 15.4 — first reticle vline
RULE_W_MM = 2.5                                    # per spec in CLAUDE.md
TEXT_X_MM = RULE_X_MM + RULE_W_MM + r.RETICLE_GUTTER_MM  # 21.9
TEXT_MAX_W_MM = (r.MARGIN_MM + r.CONTENT_W_MM) - TEXT_X_MM   # 112.1

# Tipo baseline = bottom of reticle row 1; title cap-top = top of row 2.
# The 4mm reticle gutter between them is the natural gap.
TIPO_Y_MM = _ROW_1_BOTTOM_Y
_TITLE_CAP_RATIO = 0.7165   # Lato
TITLE_Y_MM = (
    _ROW_2_TOP_Y
    + _TITLE_CAP_RATIO * TEXT_STYLES["20-Ficha-Titulo-Pieza"].size_pt * r.MM_PER_PT
)

# Cap-height ratio for sizing the red rule top edge from tipo.
_TIPO_CAP_RATIO = 0.685     # EB Garamond Italic

# Image frame: 6×4 reticle squares — all 6 columns × rows 3–6 (one row
# up from the original 4–7 to make room for the moved-down caption).
FRAME_X_MM = _RETICLE_LEFT_X_MM                              # 15.4
FRAME_Y_MM = ch.row_top(3)                                   # 56.11
FRAME_W_MM = _RETICLE_RIGHT_X_MM - _RETICLE_LEFT_X_MM        # 117.2
FRAME_H_MM = ch.row_bottom(6) - ch.row_top(3)                # 77.44 = 4 rows + 3 gutters
FRAME_INSET_MM = 4                                            # padding for internal labels

# Caption sits in row 7 (one row up from row 8): cap-top on the row's
# top line, left edge on col 1, max width = full reticle width.
_CAPTION_STYLE = TEXT_STYLES["23-Ficha-Epigrafe-Imagen"]
_CAPTION_CAP_HEIGHT_MM = (
    _CAPTION_STYLE.size_pt * 0.685 * r.MM_PER_PT             # EB Garamond Italic
)
CAPTION_ANCHOR_X_MM = _RETICLE_LEFT_X_MM                              # 15.4
CAPTION_ANCHOR_Y_MM = ch.row_top(7) + _CAPTION_CAP_HEIGHT_MM
CAPTION_MAX_W_MM = _RETICLE_RIGHT_X_MM - CAPTION_ANCHOR_X_MM          # full width


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    cabecera_sub = str(data.get("cabecera_sub", "")).strip()
    tipo = str(data.get("tipo", "")).strip()
    titulo = str(data.get("titulo", "")).strip()
    image_href = str(data.get("image", "")).strip()
    categoria = str(data.get("categoria", "A")).strip()
    caption = str(data.get("caption", "nota al pie")).strip()

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top chrome
    parts.append(ch.cabecera(pieza_id, cabecera_sub))

    # — Red vertical rule alongside tipo + title. Spans the tipo's
    #   cap-top (or the title's cap-top if no tipo) down to the bottom
    #   of row 2.
    tipo_style = TEXT_STYLES["19-Ficha-Tipo"]
    title_style = TEXT_STYLES["20-Ficha-Titulo-Pieza"]
    tipo_cap_top = TIPO_Y_MM - _TIPO_CAP_RATIO * tipo_style.size_pt * r.MM_PER_PT
    title_cap_top = TITLE_Y_MM - _TITLE_CAP_RATIO * title_style.size_pt * r.MM_PER_PT
    rule_top = tipo_cap_top if tipo else title_cap_top
    rule_h = _ROW_2_BOTTOM_Y - rule_top
    parts.append(r.red_rule_vertical(RULE_X_MM, rule_top, rule_h, width_mm=RULE_W_MM))

    if tipo:
        parts.append(r.text(
            "19-Ficha-Tipo", tipo,
            x_mm=TEXT_X_MM, y_mm=TIPO_Y_MM,
        ))
    if titulo:
        parts.append(r.text(
            "20-Ficha-Titulo-Pieza", titulo,
            x_mm=TEXT_X_MM, y_mm=TITLE_Y_MM,
            max_width_mm=TEXT_MAX_W_MM,
        ))

    # — Image: real <image> when provided, otherwise the placeholder
    if image_href:
        parts.append(
            f'<image x="{FRAME_X_MM}" y="{FRAME_Y_MM}" '
            f'width="{FRAME_W_MM}" height="{FRAME_H_MM}" '
            f'href="{image_href}" preserveAspectRatio="xMidYMid slice"/>'
        )
    else:
        parts.extend(_image_placeholder(pieza_id, categoria))

    # — Caption (row 7, left-aligned, hyphenated wrap)
    parts.append(r.text(
        "23-Ficha-Epigrafe-Imagen", caption,
        x_mm=CAPTION_ANCHOR_X_MM, y_mm=CAPTION_ANCHOR_Y_MM,
        max_width_mm=CAPTION_MAX_W_MM,
        align="start",
    ))

    # — Bottom chrome
    parts.append(r.folio(page_id))

    parts.append(r.svg_close())
    return "".join(parts)


def _image_placeholder(pieza_id: str, categoria: str) -> list[str]:
    """Empty image frame with the same internal labels as the reference."""
    out: list[str] = [
        r.image_placeholder(FRAME_X_MM, FRAME_Y_MM, FRAME_W_MM, FRAME_H_MM),
    ]

    # Top-left label: "L001  ·  ESPACIO DE IMAGEN PRINCIPAL" (gray, start)
    if pieza_id:
        out.append(_label_start(
            f"{pieza_id}  ·  Espacio de imagen principal",
            x_mm=FRAME_X_MM + FRAME_INSET_MM,
            y_mm=FRAME_Y_MM + FRAME_INSET_MM + 2,
            color=r.PALETTE["gris_texto"],
        ))

    # Center: tiny icon-rect + italic hint text
    cx = FRAME_X_MM + FRAME_W_MM / 2
    cy = FRAME_Y_MM + FRAME_H_MM / 2
    icon_w = 6
    icon_h = 4
    out.append(
        f'<rect x="{cx - icon_w/2:.3f}" y="{cy - icon_h:.3f}" '
        f'width="{icon_w}" height="{icon_h}" fill="none" '
        f'stroke="{r.PALETTE["gris_texto"]}" '
        f'stroke-width="{0.5 * r.MM_PER_PT:.4f}"/>'
    )
    out.append(_centered_italic(
        "Imagen disponible — completar en composición",
        x_mm=cx, y_mm=cy + 4,
        color=r.PALETTE["gris_texto"],
        size_pt=8,
    ))

    # Bottom-right: "CATEGORÍA X" (gray, end)
    out.append(r.text(
        "18-Ficha-Cabecera-Sub",
        f"Categoría {categoria}",
        x_mm=FRAME_X_MM + FRAME_W_MM - FRAME_INSET_MM,
        y_mm=FRAME_Y_MM + FRAME_H_MM - FRAME_INSET_MM,
    ))
    return out


# — Small inline SVG helpers for the placeholder internals —

def _label_start(text_str: str, x_mm: float, y_mm: float, color: str) -> str:
    """Lato Black 6.5pt tracking +150 uppercase, start-aligned, given color."""
    size_pt = 6.5
    ls_pt = 150 / 1000 * size_pt
    return (
        f'<text x="{x_mm}" y="{y_mm}" '
        f'font-family="{r.font_family_css("Lato", 900)}" font-weight="900" '
        f'font-size="{size_pt * r.MM_PER_PT:.4f}" '
        f'fill="{color}" text-anchor="start" '
        f'letter-spacing="{ls_pt * r.MM_PER_PT:.5f}">'
        f'{text_str.upper()}</text>'
    )


def _centered_italic(text_str: str, x_mm: float, y_mm: float,
                     color: str, size_pt: float) -> str:
    """EB Garamond Italic, centered."""
    return (
        f'<text x="{x_mm}" y="{y_mm}" '
        f'font-family="{r.font_family_css("EB Garamond")}" font-style="italic" font-weight="400" '
        f'font-size="{size_pt * r.MM_PER_PT:.4f}" '
        f'fill="{color}" text-anchor="middle">{text_str}</text>'
    )
