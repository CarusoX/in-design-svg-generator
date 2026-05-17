"""Core SVG-building helpers: A5 trim + bleed frame, mm units, text/graphics.

Templates import the constants and helpers here rather than redefining them so
the page format stays consistent across the catalog.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .styles import PALETTE, TEXT_STYLES, TextStyle

TRIM_W_MM = 148
TRIM_H_MM = 210
BLEED_MM = 0   # no bleed — SVG canvas matches A5 trim exactly
MARGIN_MM = 14

CANVAS_W_MM = TRIM_W_MM + 2 * BLEED_MM   # 154
CANVAS_H_MM = TRIM_H_MM + 2 * BLEED_MM   # 216

CONTENT_X_MM = MARGIN_MM                          # 14
CONTENT_Y_MM = MARGIN_MM                          # 14
CONTENT_W_MM = TRIM_W_MM - 2 * MARGIN_MM          # 120
CONTENT_H_MM = TRIM_H_MM - 2 * MARGIN_MM          # 182

MM_PER_PT = 0.352778
PT_PER_MM = 2.83465

# Origin (0, 0) is the top-left of the trim; viewBox extends out by BLEED on
# each side so artwork can run to the bleed.
VIEWBOX = f"{-BLEED_MM} {-BLEED_MM} {CANVAS_W_MM} {CANVAS_H_MM}"


def svg_open(background_hex: str) -> str:
    """Open <svg> with the standard A5 viewBox and a paper-color background."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{CANVAS_W_MM}mm" height="{CANVAS_H_MM}mm" '
        f'viewBox="{VIEWBOX}">'
        f'<rect x="{-BLEED_MM}" y="{-BLEED_MM}" '
        f'width="{CANVAS_W_MM}" height="{CANVAS_H_MM}" '
        f'fill="{background_hex}"/>'
    )


def svg_close() -> str:
    return "</svg>"


# — Text rendering —

# Browser font-family fallback chains.
#
# - EB Garamond: the Homebrew cask installs the old-style optical-size
#   variants, which macOS registers as "EB Garamond 12" / "EB Garamond 08"
#   rather than just "EB Garamond". The modern preferred name is in the
#   font's typo-family slot, which Safari/WebKit doesn't always honour.
# - Lato: Chrome/Safari sometimes fail to resolve `font-weight: 900` to
#   Lato Black when only the family name "Lato" is supplied. Prepending
#   the weight-specific subfamily name ("Lato Black", "Lato Bold", …) lets
#   the browser find the correct variant directly.
# - Caveat: installs cleanly as a single family.

_EB_GARAMOND_FALLBACK = (
    "'EB Garamond', 'EB Garamond 12', 'EB Garamond 08', Garamond, serif"
)

# Only heavy weights (≥500) get a weight-specific named-family prefix.
# Regular (400) and lighter resolve via plain "Lato" + the browser's
# default weight matching.
_LATO_HEAVY_WEIGHT_NAMES: list[tuple[int, str]] = [
    (900, "Black"),
    (800, "Heavy"),
    (700, "Bold"),
    (600, "Semibold"),
    (500, "Medium"),
]


def font_family_css(family: str, weight: int = 400) -> str:
    """CSS font-family value with sensible fallbacks for `family`/`weight`.

    For Lato, the weight-named subfamily (e.g. "Lato Black" at weight 900) is
    prepended so browsers that don't resolve weight on the bare "Lato"
    family still find the right variant."""
    if family == "EB Garamond":
        return _EB_GARAMOND_FALLBACK
    if family == "Caveat":
        return "Caveat, cursive"
    if family == "Lato":
        for floor, suffix in _LATO_HEAVY_WEIGHT_NAMES:
            if weight >= floor:
                return f"'Lato {suffix}', Lato, sans-serif"
        return "Lato, sans-serif"
    return family


def _letter_spacing_pt(style: TextStyle) -> float:
    return style.tracking_per1000 / 1000.0 * style.size_pt


def _char_factor(style: TextStyle) -> float:
    """Rough average glyph-width as a fraction of em, by family/weight/style.

    Used only for greedy word-wrap. The browser/renderer does the real
    layout; this just decides where to break lines. Tuned empirically against
    the reference catalog (page 6) so titles and quotes break in the same
    places."""
    fam = style.font_family.lower()
    if "lato" in fam:
        # Tuned so "Imprenta y palabra en el Virreinato" (35 chars at 20pt
        # Lato Black) fits one line in the 120mm content box — matches the
        # reference page 11 portadilla.
        return 0.48 if style.font_weight >= 900 else 0.46
    if "garamond" in fam:
        # Italic factor tuned against tests/ground-truth/Section1.svg so the
        # Sala I curatorial quote wraps to 3 lines like the reference.
        return 0.37 if style.font_style == "italic" else 0.46
    if "caveat" in fam:
        return 0.42
    return 0.50


def wrap_lines(text_str: str, style: TextStyle, max_width_mm: float) -> list[str]:
    """Greedy word-wrap to fit within max_width_mm given the style's metrics."""
    char_pt = style.size_pt * _char_factor(style) + _letter_spacing_pt(style)
    char_mm = char_pt * MM_PER_PT
    if char_mm <= 0:
        return [text_str]
    max_chars = max(1, int(max_width_mm / char_mm))

    words = text_str.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        added = len(word) + (1 if current else 0)
        if current and current_len + added > max_chars:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += added
    if current:
        lines.append(" ".join(current))
    return lines


def text(
    style_id: str,
    body,
    x_mm: float,
    y_mm: float,
    max_width_mm: float | None = None,
) -> str:
    """Emit a styled <text> block at baseline (x_mm, y_mm).

    `body` may be a single string (split on \\n, then auto-wrapped if
    max_width_mm is given) or a list of strings (each rendered as its own
    line). Uppercase is pre-applied in Python — never via CSS, since InDesign
    discards text-transform on import.
    """
    style = TEXT_STYLES[style_id]
    fill = PALETTE[style.color]

    if isinstance(body, str):
        if "\n" in body:
            lines = body.split("\n")
        elif max_width_mm is not None:
            lines = wrap_lines(body, style, max_width_mm)
        else:
            lines = [body]
    else:
        lines = list(body)

    if style.uppercase:
        lines = [line.upper() for line in lines]

    leading_pt = style.leading_pt if style.leading_pt else style.size_pt * 1.2
    ls_pt = _letter_spacing_pt(style)

    # IMPORTANT: emit all sizes as unitless user-units (= mm in our viewBox).
    # Don't use "pt" suffix here — browsers apply the CSS pt→user-unit ratio
    # (1pt = 1.333 user units) which is wrong when the viewBox is in mm.
    size_mm = style.size_pt * MM_PER_PT
    ls_mm = ls_pt * MM_PER_PT
    leading_mm = leading_pt * MM_PER_PT

    attrs = [
        f'font-family="{font_family_css(style.font_family, style.font_weight)}"',
        f'font-size="{size_mm:.4f}"',
        f'font-weight="{style.font_weight}"',
        f'fill="{fill}"',
        f'text-anchor="{style.align}"',
    ]
    if style.font_style != "normal":
        attrs.append(f'font-style="{style.font_style}"')
    if ls_mm:
        attrs.append(f'letter-spacing="{ls_mm:.5f}"')

    # Justified text: every line gets textLength + lengthAdjust="spacing"
    # so the browser distributes spacing using its own font metrics — the
    # only renderer we ship through that needs to match the layout exactly
    # (InDesign re-flows on import). For multi-line paragraphs the last
    # line stays ragged (standard convention); for a single-line block
    # (e.g. a title), the only line IS the one to justify.
    justify = style.justified and max_width_mm is not None

    parts = [f'<text x="{x_mm}" y="{y_mm}" {" ".join(attrs)}>']
    last_idx = len(lines) - 1
    single_line = len(lines) == 1
    for i, line in enumerate(lines):
        dy = "0" if i == 0 else f"{leading_mm:.4f}"
        justify_line = justify and (single_line or i < last_idx)
        if justify_line:
            parts.append(
                f'<tspan x="{x_mm}" dy="{dy}" '
                f'textLength="{max_width_mm:.4f}" lengthAdjust="spacing">'
                f'{escape(line)}</tspan>'
            )
        else:
            parts.append(f'<tspan x="{x_mm}" dy="{dy}">{escape(line)}</tspan>')
    parts.append('</text>')
    return "".join(parts)


def paragraph(
    style_id: str,
    text_str: str,
    x_mm: float,
    y_mm: float,
    max_width_mm: float,
    first_line_indent_mm: float = 0,
    hanging_indent_mm: float = 0,
) -> tuple[str, float]:
    """Render a single paragraph and return (svg, total_height_mm).

    - `first_line_indent_mm` shifts the first line to the right (positive value
      = traditional paragraph indent).
    - `hanging_indent_mm` shifts every line AFTER the first to the right
      (positive value = bibliography-style hanging indent).
    - The two are independent and can both be zero. `total_height_mm` is the
      baseline-to-baseline distance from the first line to where a following
      paragraph's first baseline would sit if placed at `y_mm + height`.
    """
    style = TEXT_STYLES[style_id]
    fill = PALETTE[style.color]
    leading_pt = style.leading_pt if style.leading_pt else style.size_pt * 1.2
    leading_mm = leading_pt * MM_PER_PT
    size_mm = style.size_pt * MM_PER_PT
    ls_pt = _letter_spacing_pt(style)
    ls_mm = ls_pt * MM_PER_PT

    # Word-wrap with two widths: first line narrower if indented, subsequent
    # lines narrower if hanging-indented.
    char_pt = style.size_pt * _char_factor(style) + ls_pt
    char_mm = char_pt * MM_PER_PT
    first_w = max(1.0, max_width_mm - first_line_indent_mm)
    rest_w = max(1.0, max_width_mm - hanging_indent_mm)
    first_max = max(1, int(first_w / char_mm)) if char_mm > 0 else 80
    rest_max = max(1, int(rest_w / char_mm)) if char_mm > 0 else 80

    words = text_str.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    current_max = first_max
    for word in words:
        added = len(word) + (1 if current else 0)
        if current and current_len + added > current_max:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
            current_max = rest_max
        else:
            current.append(word)
            current_len += added
    if current:
        lines.append(" ".join(current))

    if style.uppercase:
        lines = [line.upper() for line in lines]

    attrs = [
        f'font-family="{font_family_css(style.font_family, style.font_weight)}"',
        f'font-size="{size_mm:.4f}"',
        f'font-weight="{style.font_weight}"',
        f'fill="{fill}"',
        f'text-anchor="{style.align}"',
    ]
    if style.font_style != "normal":
        attrs.append(f'font-style="{style.font_style}"')
    if ls_mm:
        attrs.append(f'letter-spacing="{ls_mm:.5f}"')

    # Justified text: every line except the last is stretched to fit its
    # available width via SVG's `textLength` + `lengthAdjust="spacing"`.
    # First-line indent reduces the available width on line 1; hanging
    # indent reduces it on every later line.
    justify = style.justified and len(lines) > 1
    first_w_mm = max_width_mm - first_line_indent_mm
    rest_w_mm = max_width_mm - hanging_indent_mm

    parts = [f'<text x="{x_mm}" y="{y_mm}" {" ".join(attrs)}>']
    last_idx = len(lines) - 1
    for i, line in enumerate(lines):
        if i == 0:
            line_x = x_mm + first_line_indent_mm
            line_w = first_w_mm
        else:
            line_x = x_mm + hanging_indent_mm
            line_w = rest_w_mm
        dy = "0" if i == 0 else f"{leading_mm:.4f}"
        extra = (
            f' textLength="{line_w}" lengthAdjust="spacing"'
            if justify and i < last_idx else ''
        )
        parts.append(
            f'<tspan x="{line_x}" dy="{dy}"{extra}>{escape(line)}</tspan>'
        )
    parts.append('</text>')

    # Height = distance from first baseline to (next paragraph's) first
    # baseline, which is N×leading where N is the number of rendered lines.
    height_mm = len(lines) * leading_mm
    return "".join(parts), height_mm


# — Graphic element helpers (decorative) —

def red_rule_vertical(x_mm: float, y_mm: float, height_mm: float, width_mm: float = 2.5) -> str:
    return (
        f'<rect x="{x_mm}" y="{y_mm}" width="{width_mm}" height="{height_mm}" '
        f'fill="{PALETTE["rojo_tinta"]}"/>'
    )


def ficha_header_rule(y_mm: float, x_mm: float = MARGIN_MM, length_mm: float = CONTENT_W_MM) -> str:
    # 0.4pt stroke, expressed in mm (user units).
    return (
        f'<line x1="{x_mm}" y1="{y_mm}" x2="{x_mm + length_mm}" y2="{y_mm}" '
        f'stroke="{PALETTE["negro_tinta"]}" stroke-width="{0.4 * MM_PER_PT:.4f}"/>'
    )


def ficha_footer_rule(y_mm: float, x_mm: float = MARGIN_MM, length_mm: float = CONTENT_W_MM) -> str:
    return (
        f'<line x1="{x_mm}" y1="{y_mm}" x2="{x_mm + length_mm}" y2="{y_mm}" '
        f'stroke="{PALETTE["rojo_tinta"]}" stroke-width="{0.3 * MM_PER_PT:.4f}"/>'
    )


def image_placeholder(x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> str:
    return (
        f'<rect x="{x_mm}" y="{y_mm}" width="{w_mm}" height="{h_mm}" '
        f'fill="{PALETTE["frame_fill"]}" stroke="{PALETTE["frame_stroke"]}" '
        f'stroke-width="{0.4 * MM_PER_PT:.4f}"/>'
    )


# — Reticle (preview-only grid overlay) —
#
# Sits inside the content box with a 1.4mm inset on all sides. Divides the
# remaining area into RETICLE_COLS × RETICLE_ROWS cells separated by
# RETICLE_GUTTER_MM gutters. Each cell boundary is drawn as a thin line
# that spans the full page (not just the reticle area) so the grid is easy
# to read against the layout.

RETICLE_INSET_MM = 1.4
RETICLE_COLS = 6
RETICLE_ROWS = 9
RETICLE_GUTTER_MM = 4.0   # 0.4 cm
# White lines + `mix-blend-mode: difference` in the preview CSS make the
# reticle invert whatever's behind it — readable on cream and on red.
RETICLE_STROKE = "#FFFFFF"
RETICLE_STROKE_WIDTH_MM = 0.05
RETICLE_OPACITY = 0.6


def reticle_svg() -> str:
    """Return a full <svg>…</svg> with the column/row reticle. Sized to A5
    so it can be overlaid on any page in the preview."""
    left = MARGIN_MM + RETICLE_INSET_MM
    right = TRIM_W_MM - MARGIN_MM - RETICLE_INSET_MM
    top = MARGIN_MM + RETICLE_INSET_MM
    bottom = TRIM_H_MM - MARGIN_MM - RETICLE_INSET_MM

    col_w = (right - left - (RETICLE_COLS - 1) * RETICLE_GUTTER_MM) / RETICLE_COLS
    row_h = (bottom - top - (RETICLE_ROWS - 1) * RETICLE_GUTTER_MM) / RETICLE_ROWS

    # Compute every vertical cell-boundary x: outer-left, then (right-of-col,
    # left-of-next-col) pairs across each gutter, then outer-right.
    v_xs: list[float] = [left]
    cursor = left
    for _ in range(RETICLE_COLS - 1):
        cursor += col_w
        v_xs.append(cursor)
        cursor += RETICLE_GUTTER_MM
        v_xs.append(cursor)
    v_xs.append(right)

    h_ys: list[float] = [top]
    cursor = top
    for _ in range(RETICLE_ROWS - 1):
        cursor += row_h
        h_ys.append(cursor)
        cursor += RETICLE_GUTTER_MM
        h_ys.append(cursor)
    h_ys.append(bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{TRIM_W_MM}mm" height="{TRIM_H_MM}mm" '
        f'viewBox="0 0 {TRIM_W_MM} {TRIM_H_MM}">',
        f'<g stroke="{RETICLE_STROKE}" '
        f'stroke-width="{RETICLE_STROKE_WIDTH_MM}" '
        f'fill="none" opacity="{RETICLE_OPACITY}">',
    ]
    for x in v_xs:
        parts.append(f'<line x1="{x:.4f}" y1="0" x2="{x:.4f}" y2="{TRIM_H_MM}"/>')
    for y in h_ys:
        parts.append(f'<line x1="0" y1="{y:.4f}" x2="{TRIM_W_MM}" y2="{y:.4f}"/>')
    parts.append('</g></svg>')
    return "".join(parts)
