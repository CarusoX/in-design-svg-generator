"""Ficha — image side (left page of an artwork spread).

Layout mirrors reference page 7:
- Top cabecera + horizontal rule (shared with ficha_texto).
- Red vertical rule + tipo + Lato Black title.
- Italic serif autor line + regular serif data line.
- Large image placeholder frame (or real image when provided).
  Frame carries small internal labels: ID top-left, "categoría X" bottom-right,
  centered "imagen disponible…" hint.
- Caption with red curly bracket below the frame.
- Folio strip at the bottom (shared).

Expected `data` keys:
    pieza_id (str)       — e.g. "L001"
    cabecera_sub (str)   — e.g. "Orígenes y sustratos prehispánicos (Pre-1764)"
    tipo (str)           — italic serif eyebrow, red
    titulo (str)         — artwork title (auto-wraps to 2 lines if needed)
    autor (str)          — italic serif
    datos (str)          — regular serif gray, auto-wraps
    image (str, opt.)    — relative path to the placed image; when absent,
                            the placeholder frame is drawn
    categoria (str)      — e.g. "A", "B" (defaults to "A")
    caption (str)        — caption text after the bracket (no need to repeat
                            the pieza_id — the template prepends it)
"""

from __future__ import annotations

from xml.sax.saxutils import escape

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
_row_top = ch.row_top
_row_bottom = ch.row_bottom

# Horizontal positions for the tipo/title block:
#   - Red rule left edge sits on the first vertical reticle line.
#   - Text starts one reticle gutter (4mm) past the rule's right edge.
RULE_X_MM = r.MARGIN_MM + r.RETICLE_INSET_MM      # 15.4 — first reticle vline
RULE_W_MM = 2.5                                    # per spec in CLAUDE.md
TEXT_X_MM = RULE_X_MM + RULE_W_MM + r.RETICLE_GUTTER_MM  # 21.9
TEXT_MAX_W_MM = (r.MARGIN_MM + r.CONTENT_W_MM) - TEXT_X_MM   # 112.1

# Tipo baseline = bottom of reticle row 1 (= top of gutter 1).
# Title cap-top = top of reticle row 2 (= bottom of gutter 1).
# So the 4mm gap between them lands exactly on the reticle gutter.
# Title's baseline = cap_top + cap_height (Lato cap-height ≈ 0.7165 × em).
TIPO_Y_MM = _ROW_1_BOTTOM_Y
TITLE_Y_MM = (
    _ROW_2_TOP_Y
    + 0.7165 * TEXT_STYLES["20-Ficha-Titulo-Pieza"].size_pt * r.MM_PER_PT
)

# For sizing the red rule height: cap-height / descender ratios per font.
_TIPO_CAP_RATIO = 0.685     # EB Garamond Italic
_TITLE_DESC_RATIO = 0.27    # generous descender allowance

# Autor sits at the TOP-LEFT corner of cell (row 3, col 1): cap-top on
# the row's top line so the text rides inside the row.
AUTOR_X_MM = _RETICLE_LEFT_X_MM                                       # 15.4
_AUTOR_STYLE = TEXT_STYLES["21-Ficha-Subtitulo-Autor"]
_AUTOR_CAP_HEIGHT_MM = _AUTOR_STYLE.size_pt * 0.685 * r.MM_PER_PT      # EB Gar. Italic
AUTOR_Y_MM = _row_top(3) + _AUTOR_CAP_HEIGHT_MM

# Datos sits one reticle gutter (0.4cm = 4mm of *visible* gap) below
# autor — measured from autor's descender bottom to datos' cap-top.
_DATOS_STYLE = TEXT_STYLES["22-Ficha-Subtitulo-Datos"]
_DATOS_CAP_HEIGHT_MM = _DATOS_STYLE.size_pt * 0.685 * r.MM_PER_PT     # EB Garamond
_AUTOR_DESCENDER_MM = _AUTOR_STYLE.size_pt * 0.21 * r.MM_PER_PT       # ≈ Garamond italic
DATOS_X_MM = _RETICLE_LEFT_X_MM                                       # 15.4
DATOS_Y_MM = (
    AUTOR_Y_MM + _AUTOR_DESCENDER_MM   # autor's visible bottom
    + r.RETICLE_GUTTER_MM              # 4mm visible gap
    + _DATOS_CAP_HEIGHT_MM             # then drop to datos baseline
)

# Image frame: 6×4 reticle squares — all 6 columns (full reticle width)
# × rows 4–7 (4 squares tall, sharing 3 internal row gutters).
FRAME_X_MM = _RETICLE_LEFT_X_MM                              # 15.4
FRAME_Y_MM = _row_top(4)                                     # 76.47
FRAME_W_MM = _RETICLE_RIGHT_X_MM - _RETICLE_LEFT_X_MM        # 117.2
FRAME_H_MM = _row_bottom(7) - _row_top(4)                    # 77.44 = 4 rows + 3 gutters
FRAME_INSET_MM = 4                                            # padding for internal labels

# Footer chrome — caption and ESTADO both sit in row 8 with their
# cap-tops on the row's top line. Caption takes cols 1–3 (left half of
# the page), ESTADO takes cols 4–6 (right half). Each block left-aligns
# inside its 3-column box; long strings hyphenate to wrap rather than
# overflow.
_CAPTION_STYLE = TEXT_STYLES["23-Ficha-Epigrafe-Imagen"]
_CAPTION_CAP_RATIO = 0.685   # EB Garamond Italic
_CAPTION_CAP_HEIGHT_MM = (
    _CAPTION_STYLE.size_pt * _CAPTION_CAP_RATIO * r.MM_PER_PT
)
_FOOTER_Y_MM = ch.row_top(8) + _CAPTION_CAP_HEIGHT_MM

CAPTION_ANCHOR_X_MM = _RETICLE_LEFT_X_MM                              # 15.4
CAPTION_ANCHOR_Y_MM = _FOOTER_Y_MM
CAPTION_MAX_W_MM = r.RETICLE_COL_RIGHT_X_MM[2] - CAPTION_ANCHOR_X_MM  # cols 1–3

# ESTADO starts at col 4's left edge (= col 3 right + gutter).
ESTADO_X_MM = r.RETICLE_COL_RIGHT_X_MM[2] + r.RETICLE_GUTTER_MM       # 76.0
ESTADO_Y_MM = _FOOTER_Y_MM
ESTADO_MAX_W_MM = _RETICLE_RIGHT_X_MM - ESTADO_X_MM                   # cols 4–6


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    cabecera_sub = str(data.get("cabecera_sub", "")).strip()
    tipo = str(data.get("tipo", "")).strip()
    titulo = str(data.get("titulo", "")).strip()
    autor = str(data.get("autor", "")).strip()
    datos = str(data.get("datos", "")).strip()
    image_href = str(data.get("image", "")).strip()
    categoria = str(data.get("categoria", "A")).strip()
    caption = str(data.get("caption", "nota al pie")).strip()
    estado = str(data.get("estado", "")).strip()

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top chrome
    parts.append(ch.cabecera(pieza_id, cabecera_sub))

    # — Red vertical rule alongside tipo + title.
    #   Spans from the tipo's cap-top down to the bottom of reticle row 2
    #   (the row the title lives in). Height is fixed regardless of how
    #   many lines the title wraps to.
    tipo_style = TEXT_STYLES["19-Ficha-Tipo"]
    title_style = TEXT_STYLES["20-Ficha-Titulo-Pieza"]
    tipo_cap_top = TIPO_Y_MM - _TIPO_CAP_RATIO * tipo_style.size_pt * r.MM_PER_PT
    title_cap_top = TITLE_Y_MM - 0.7165 * title_style.size_pt * r.MM_PER_PT
    rule_top = tipo_cap_top if tipo else title_cap_top
    rule_h = _ROW_2_BOTTOM_Y - rule_top
    parts.append(r.red_rule_vertical(RULE_X_MM, rule_top, rule_h, width_mm=RULE_W_MM))

    if tipo:
        parts.append(r.text("19-Ficha-Tipo", tipo,
                            x_mm=TEXT_X_MM, y_mm=TIPO_Y_MM))
    if titulo:
        parts.append(r.text(
            "20-Ficha-Titulo-Pieza", titulo,
            x_mm=TEXT_X_MM, y_mm=TITLE_Y_MM,
            max_width_mm=TEXT_MAX_W_MM,
        ))

    if autor:
        parts.append(r.text("21-Ficha-Subtitulo-Autor", autor,
                            x_mm=AUTOR_X_MM, y_mm=AUTOR_Y_MM,
                            max_width_mm=_RETICLE_RIGHT_X_MM - AUTOR_X_MM))
    if datos:
        parts.append(r.text("22-Ficha-Subtitulo-Datos", datos,
                            x_mm=DATOS_X_MM, y_mm=DATOS_Y_MM,
                            max_width_mm=_RETICLE_RIGHT_X_MM - DATOS_X_MM))

    # — Image: real <image> when provided, otherwise the placeholder
    if image_href:
        parts.append(
            f'<image x="{FRAME_X_MM}" y="{FRAME_Y_MM}" '
            f'width="{FRAME_W_MM}" height="{FRAME_H_MM}" '
            f'href="{image_href}" preserveAspectRatio="xMidYMid slice"/>'
        )
    else:
        parts.extend(_image_placeholder(pieza_id, categoria))

    # — Footer row (row 8): caption left half + ESTADO right half
    parts.extend(_caption(caption))
    if estado:
        parts.append(_estado_block(estado))

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


def _caption(caption: str) -> list[str]:
    """Italic gray caption, left-aligned inside cols 1–3 of row 8.
    Wraps with Spanish hyphenation when too long for one line."""
    return [r.text(
        "23-Ficha-Epigrafe-Imagen", caption,
        x_mm=CAPTION_ANCHOR_X_MM, y_mm=CAPTION_ANCHOR_Y_MM,
        max_width_mm=CAPTION_MAX_W_MM,
        align="start",
    )]


_ESTADO_LABEL = "ESTADO:"


def _estado_block(estado: str) -> str:
    """Render 'ESTADO: <value>' inside cols 4–6 of row 8 — bold sans
    label + italic serif value (matching the caption style). The full
    string is wrapped together so hyphenation works across the label
    boundary; the label is then re-styled inline on the first line.
    """
    full = f"{_ESTADO_LABEL} {estado}"
    lines = r.wrap_lines(full, _CAPTION_STYLE, ESTADO_MAX_W_MM)
    if not lines:
        return ""

    size_mm = _CAPTION_STYLE.size_pt * r.MM_PER_PT
    leading_pt = _CAPTION_STYLE.leading_pt or _CAPTION_STYLE.size_pt * 1.2
    leading_mm = leading_pt * r.MM_PER_PT
    fill = r.PALETTE[_CAPTION_STYLE.color]
    family_italic = r.font_family_css("EB Garamond")
    family_bold = r.font_family_css("Lato", 900)

    parts = [
        f'<text x="{ESTADO_X_MM}" y="{ESTADO_Y_MM}" '
        f'fill="{fill}" text-anchor="start" '
        f'font-size="{size_mm:.4f}">',
    ]
    for i, line in enumerate(lines):
        dy = "0" if i == 0 else f"{leading_mm:.4f}"
        # Bold the LABEL only where it appears intact at the start of
        # the first line. Otherwise render the line in plain italic.
        if i == 0 and line.startswith(_ESTADO_LABEL):
            rest = line[len(_ESTADO_LABEL):]
            parts.append(
                f'<tspan x="{ESTADO_X_MM}" dy="{dy}" '
                f'font-family="{family_bold}" font-weight="900">'
                f'{_ESTADO_LABEL}</tspan>'
                f'<tspan font-family="{family_italic}" font-style="italic" '
                f'font-weight="400" xml:space="preserve">{escape(rest)}</tspan>'
            )
        else:
            parts.append(
                f'<tspan x="{ESTADO_X_MM}" dy="{dy}" '
                f'font-family="{family_italic}" font-style="italic" '
                f'font-weight="400">{escape(line)}</tspan>'
            )
    parts.append('</text>')
    return "".join(parts)


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
