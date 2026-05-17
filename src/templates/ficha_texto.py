"""Ficha — text side (right page of an artwork spread).

- Top cabecera + horizontal rule (shared with ficha_imagen).
- Metadata stack. Each entry is TWO lines:
    line 1: Autor / Estado / Fecha / Origen — EB Garamond italic red
            at 8.5pt (same family / style / color / size as the page-1
            "tipo" eyebrow), sentence-case.
    line 2: the value — Garamond regular, not italic.
  with 0.2cm between the label and its value, and 0.4cm visible gap
  between entries. All labels left-anchor at col 1.
- Autor's label baseline lands on row 1's bottom line so the stack
  starts higher and frees vertical space for the description.
- Description body has its own Descripción title, snapped to the next
  reticle row top after the metadata block ends.
- Folio strip at the bottom (shared).

Expected `data` keys:
    pieza_id (str)       — same as ficha_imagen
    cabecera_sub (str)   — same
    autor (str)          — bridged from imagen block
    estado (str)         — from texto block
    datos (str)          — bridged; split by " · " into fecha + origen
    descripcion (str)    — multi-line body, auto-wraps + hyphenates
"""

from __future__ import annotations

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


META_X_MM = ch.LEFT_X_MM                                          # 15.4
META_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM                          # 117.2
_LABEL_VALUE_GAP_MM = 2.0                                         # 0.2cm
_ITEM_GAP_MM = r.RETICLE_GUTTER_MM                                # 0.4cm between items
_GARAMOND_CAP_RATIO = 0.685
_GARAMOND_DESC_RATIO = 0.21


def _line_metrics(style):
    """(cap_height_mm, descender_mm) for a Garamond style."""
    return (
        style.size_pt * _GARAMOND_CAP_RATIO * r.MM_PER_PT,
        style.size_pt * _GARAMOND_DESC_RATIO * r.MM_PER_PT,
    )


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    cabecera_sub = str(data.get("cabecera_sub", "")).strip()
    descripcion = str(data.get("descripcion", "")).strip()
    autor = str(data.get("autor", "")).strip()
    estado = str(data.get("estado", "")).strip()
    datos = str(data.get("datos", "")).strip()
    if " · " in datos:
        fecha, origen = (s.strip() for s in datos.split(" · ", 1))
    else:
        fecha, origen = datos, ""

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top chrome
    parts.append(ch.cabecera(pieza_id, cabecera_sub))

    # — Metadata stack. Autor's label baseline lands on row 1's bottom
    #   line (bottom-left of cell (1, 1)) so the stack starts higher
    #   and saves vertical space. Every entry left-anchors at col 1;
    #   Estado / Fecha / Origen follow 0.4cm below the previous text.
    label_cap_h = _LABEL_SIZE_PT * _GARAMOND_CAP_RATIO * r.MM_PER_PT
    cap_top_y = ch.row_bottom(1) - label_cap_h
    for label, value in (
        ("Autor",  autor),
        ("Estado", estado),
        ("Fecha",  fecha),
        ("Origen", origen),
    ):
        cap_top_y = _add_meta_entry(parts, label, value, cap_top_y)

    # — Descripción: label follows the metadata stack's gap conventions
    #   (0.4cm visible gap from Origen's last value to the label cap-top,
    #   0.2cm from the label descender to the body cap-top) — NOT snapped
    #   to a reticle row, since snapping wastes a whole square whenever
    #   Estado/Origen wrap. Body rendered with r.paragraph() so paragraph
    #   breaks (split on \n from folded scalars) come out as separate runs.
    if descripcion:
        _add_descripcion(parts, descripcion, cap_top_y)

    # — Bottom chrome
    parts.append(r.folio(page_id))

    parts.append(r.svg_close())
    return "".join(parts)


_LABEL_SIZE_PT = 8.5    # matches the page-1 tipo eyebrow (style 19)
_LABEL_WEIGHT = 400
_META_VALUE_STYLE_ID = "Ficha-Meta-Value"
_DESCRIPCION_INDENT_MM = 0   # no first-line indent


def _label_svg(label: str, baseline_y: float) -> str:
    """Italic red EB Garamond label at META_X_MM, baseline at `baseline_y`."""
    label_size_mm = _LABEL_SIZE_PT * r.MM_PER_PT
    return (
        f'<text x="{META_X_MM}" y="{baseline_y:.4f}" '
        f'font-family="{r.font_family_css("EB Garamond")}" '
        f'font-style="italic" '
        f'font-weight="{_LABEL_WEIGHT}" '
        f'font-size="{label_size_mm:.4f}" '
        f'fill="{r.PALETTE["rojo_tinta"]}" '
        f'text-anchor="start">{label}</text>'
    )


def _add_descripcion(parts: list[str], descripcion: str, label_cap_top_y: float) -> None:
    """Append the 'Descripción' label followed by the body, where each
    paragraph (split on \\n) gets a 5mm first-line indent."""
    label_cap_h = _LABEL_SIZE_PT * _GARAMOND_CAP_RATIO * r.MM_PER_PT
    label_desc = _LABEL_SIZE_PT * _GARAMOND_DESC_RATIO * r.MM_PER_PT
    label_baseline = label_cap_top_y + label_cap_h
    parts.append(_label_svg("Descripción", label_baseline))

    body_style = TEXT_STYLES["24-Ficha-Descripcion"]
    body_cap_h, _ = _line_metrics(body_style)
    y = label_baseline + label_desc + _LABEL_VALUE_GAP_MM + body_cap_h

    paragraphs = [p.strip() for p in descripcion.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [descripcion]
    for paragraph in paragraphs:
        svg, height_mm = r.paragraph(
            "24-Ficha-Descripcion", paragraph,
            x_mm=META_X_MM, y_mm=y,
            max_width_mm=META_W_MM,
            first_line_indent_mm=_DESCRIPCION_INDENT_MM,
        )
        parts.append(svg)
        y += height_mm


def _add_meta_entry(
    parts: list[str], label: str, value: str, cap_top_y: float,
) -> float:
    """Append one metadata entry — EB Garamond italic red label (same
    family/style/color as the page-1 tipo eyebrow) on its own line,
    value below — and return the next entry's cap-top (last value
    descender + 0.4cm)."""
    if not value:
        return cap_top_y

    # Label (1 line, never wraps for these short labels).
    label_cap_h = _LABEL_SIZE_PT * _GARAMOND_CAP_RATIO * r.MM_PER_PT
    label_desc = _LABEL_SIZE_PT * _GARAMOND_DESC_RATIO * r.MM_PER_PT
    label_baseline = cap_top_y + label_cap_h
    parts.append(_label_svg(label, label_baseline))

    # Value (potentially multi-line; wraps + hyphenates via r.text).
    value_style = TEXT_STYLES[_META_VALUE_STYLE_ID]
    value_cap_h, value_desc = _line_metrics(value_style)
    value_cap_top = label_baseline + label_desc + _LABEL_VALUE_GAP_MM
    value_baseline = value_cap_top + value_cap_h
    parts.append(r.text(
        _META_VALUE_STYLE_ID, value,
        x_mm=META_X_MM, y_mm=value_baseline,
        max_width_mm=META_W_MM,
    ))

    # Account for value wrapping when handing off to the next entry.
    n_lines = len(r.wrap_lines(value, value_style, META_W_MM))
    leading_pt = value_style.leading_pt or value_style.size_pt * 1.2
    leading_mm = leading_pt * r.MM_PER_PT
    value_last_baseline = value_baseline + (n_lines - 1) * leading_mm
    return value_last_baseline + value_desc + _ITEM_GAP_MM
