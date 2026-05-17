"""Placeholder template.

Used until a real template is registered. Draws the A5 page chrome (trim
guide, content-box guide), the page number large in the center, and the
requested template name underneath so it's obvious which page still needs
real layout work.
"""

from .. import render as r
from ..styles import PALETTE


def render(page_id: int, data: dict) -> str:
    template_name = data.get("__template__", "placeholder")
    cx = r.TRIM_W_MM / 2
    cy = r.TRIM_H_MM / 2

    parts = [r.svg_open(PALETTE["papel_crema"])]

    # Trim guide (preview only — not for print output).
    parts.append(
        f'<rect x="0" y="0" '
        f'width="{r.TRIM_W_MM}" height="{r.TRIM_H_MM}" '
        f'fill="none" stroke="{PALETTE["gris_claro"]}" '
        f'stroke-width="0.1" stroke-dasharray="1 1"/>'
    )

    # Content-box (safe zone) guide.
    parts.append(
        f'<rect x="{r.CONTENT_X_MM}" y="{r.CONTENT_Y_MM}" '
        f'width="{r.CONTENT_W_MM}" height="{r.CONTENT_H_MM}" '
        f'fill="none" stroke="{PALETTE["frame_stroke"]}" '
        f'stroke-width="0.15" stroke-dasharray="2 2"/>'
    )

    # Big page number.
    parts.append(
        f'<text x="{cx}" y="{cy}" '
        f'font-family="Lato" font-weight="900" font-size="72pt" '
        f'fill="{PALETTE["negro_tinta"]}" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{page_id}</text>'
    )

    # Requested template name underneath.
    parts.append(
        f'<text x="{cx}" y="{cy + 20}" '
        f'font-family="Lato" font-weight="400" font-size="10pt" '
        f'fill="{PALETTE["gris_texto"]}" '
        f'text-anchor="middle">'
        f'template: {template_name}</text>'
    )

    parts.append(r.svg_close())
    return "".join(parts)
