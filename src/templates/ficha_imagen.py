"""Ficha — image side (left page of an artwork spread).

- Top cabecera + horizontal rule (shared with ficha_texto).
- Red vertical rule + tipo (red italic eyebrow) + Lato Black title.
  autor / datos / estado live on the text page now.
- One to five images, auto-placed by `src.layouts.best_layout()` — the
  layout candidate whose slots best match the images' aspect ratios
  wins. Each image is contained (preserve aspect, centered) so cream
  paper shows through where it's narrower than its slot. Missing files
  fall back to a thin placeholder rect; an empty image list shows the
  legacy single-frame placeholder for proofing.
- Folio strip at the bottom (shared). Caption rendering removed
  (the YAML `caption` field is preserved but unused).

Expected `data` keys:
    pieza_id (str)            — e.g. "L001"
    cabecera_sub (str)        — e.g. "Orígenes y sustratos prehispánicos (Pre-1764)"
    tipo (str)                — italic serif eyebrow, red
    titulo (str)              — artwork title (auto-wraps to 2 lines)
    images (list[str], opt.)  — relative paths to placed images (≤ 5).
                                For backward compat, a single `image: "..."`
                                string is treated as a 1-item list.
    categoria (str)           — e.g. "A", "B" (defaults to "A"; used
                                only by the empty-list placeholder)
    caption (str)             — kept in YAML, NOT rendered.
"""

from __future__ import annotations

from pathlib import Path

from .. import layouts
from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# Where the curator's images live in the source tree (for Pillow to read
# aspect ratios from). The build step copies these to out/images/ on
# every generate so the SVG href below resolves on the friend's machine.
SOURCE_IMAGES_REL = "reference/imagenes"
# Path that goes into the SVG's <image href="..."> — relative to the
# SVG's location (out/page-NNN.svg → out/images/<file>).
HREF_IMAGES_DIR = "images"

# Reticle row math comes from ch (shared). Cached aliases.
_ROW_2_TOP_Y = ch.row_top(2)
_ROW_2_BOTTOM_Y = ch.row_bottom(2)

# Horizontal positions for the tipo/title block.
RULE_X_MM = r.MARGIN_MM + r.RETICLE_INSET_MM      # 15.4
RULE_W_MM = 2.5
TEXT_X_MM = RULE_X_MM + RULE_W_MM + r.RETICLE_GUTTER_MM  # 21.9
TEXT_MAX_W_MM = (r.MARGIN_MM + r.CONTENT_W_MM) - TEXT_X_MM   # 112.1

TIPO_Y_MM = ch.row_bottom(1)
_TITLE_CAP_RATIO = 0.7165
TITLE_Y_MM = (
    _ROW_2_TOP_Y
    + _TITLE_CAP_RATIO * TEXT_STYLES["20-Ficha-Titulo-Pieza"].size_pt * r.MM_PER_PT
)
_TIPO_CAP_RATIO = 0.685

# Slot the empty-list placeholder occupies (= 6 cols × 4 rows, the
# original frame size). Used only when `images` is empty / absent.
_PLACEHOLDER_SLOT: layouts.Slot = (1, 3, 6, 4)
_PLACEHOLDER_INSET_MM = 4

MAX_IMAGES = 5


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    cabecera_sub = str(data.get("cabecera_sub", "")).strip()
    tipo = str(data.get("tipo", "")).strip()
    titulo = str(data.get("titulo", "")).strip()
    categoria = str(data.get("categoria", "A")).strip()
    images = _coerce_images(data)

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top chrome
    parts.append(ch.cabecera(pieza_id, cabecera_sub))

    # — Red vertical rule + tipo + title
    tipo_style = TEXT_STYLES["19-Ficha-Tipo"]
    title_style = TEXT_STYLES["20-Ficha-Titulo-Pieza"]
    tipo_cap_top = TIPO_Y_MM - _TIPO_CAP_RATIO * tipo_style.size_pt * r.MM_PER_PT
    title_cap_top = TITLE_Y_MM - _TITLE_CAP_RATIO * title_style.size_pt * r.MM_PER_PT
    rule_top = tipo_cap_top if tipo else title_cap_top
    rule_h = _ROW_2_BOTTOM_Y - rule_top
    parts.append(r.red_rule_vertical(RULE_X_MM, rule_top, rule_h, width_mm=RULE_W_MM))

    if tipo:
        parts.append(r.text("19-Ficha-Tipo", tipo, x_mm=TEXT_X_MM, y_mm=TIPO_Y_MM))
    if titulo:
        parts.append(r.text(
            "20-Ficha-Titulo-Pieza", titulo,
            x_mm=TEXT_X_MM, y_mm=TITLE_Y_MM,
            max_width_mm=TEXT_MAX_W_MM,
        ))

    # — Images (auto-layout) or legacy placeholder when none
    parts.extend(_render_images(images, pieza_id, categoria))

    # — Bottom chrome
    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)


def _coerce_images(data: dict) -> list[str]:
    """Read the image list. Accepts `images: [path, …]` (preferred) or a
    single `image: "path"` string for backward compat. Returns a list
    of non-empty stripped strings."""
    raw = data.get("images")
    if raw is None:
        single = data.get("image")
        raw = [single] if single else []
    elif not isinstance(raw, (list, tuple)):
        raw = [raw]
    paths = [str(p).strip() for p in raw if p and str(p).strip()]
    if len(paths) > MAX_IMAGES:
        raise ValueError(
            f"ficha_imagen supports up to {MAX_IMAGES} images, got {len(paths)}"
        )
    return paths


def _render_images(images: list[str], pieza_id: str, categoria: str) -> list[str]:
    """Pick the best layout for `images`, render each contained inside
    its slot. YAML entries are stripped to their basename: aspect read
    from reference/imagenes/<file>, href emitted as images/<file>
    (resolves against the SVG's own dir, which receives a copy via
    `generate.sync_images()`). Missing source files fall back to a
    plain placeholder rect; an empty list shows the legacy proof
    placeholder."""
    if not images:
        return _empty_placeholder(pieza_id, categoria)

    basenames = [Path(p).name for p in images]
    source_rel = [f"{SOURCE_IMAGES_REL}/{name}" for name in basenames]
    aspects = [layouts.image_aspect(p, PROJECT_ROOT) for p in source_rel]
    layout = layouts.best_layout(len(images), aspects)
    if layout is None:                       # shouldn't happen — guarded by MAX
        return _empty_placeholder(pieza_id, categoria)

    out: list[str] = []
    for name, src_rel, slot in zip(basenames, source_rel, layout):
        x, y, w, h = layouts.slot_mm(slot)
        if (PROJECT_ROOT / src_rel).exists():
            # Contained (preserve aspect, centered) — cream paper shows
            # through where the image is narrower than its slot.
            href = f"{HREF_IMAGES_DIR}/{name}"
            out.append(
                f'<image x="{x:.4f}" y="{y:.4f}" '
                f'width="{w:.4f}" height="{h:.4f}" '
                f'href="{href}" preserveAspectRatio="xMidYMid meet"/>'
            )
        else:
            out.append(r.image_placeholder(x, y, w, h))
    return out


def _empty_placeholder(pieza_id: str, categoria: str) -> list[str]:
    """The legacy proof placeholder — used when no images are specified.
    A single 6×4 frame with ID label, center hint, and categoría tag."""
    x, y, w, h = layouts.slot_mm(_PLACEHOLDER_SLOT)
    out: list[str] = [r.image_placeholder(x, y, w, h)]

    # Top-left ID label
    if pieza_id:
        out.append(_label_start(
            f"{pieza_id}  ·  Espacio de imagen principal",
            x_mm=x + _PLACEHOLDER_INSET_MM,
            y_mm=y + _PLACEHOLDER_INSET_MM + 2,
            color=r.PALETTE["gris_texto"],
        ))

    # Center icon-rect + italic hint
    cx, cy = x + w / 2, y + h / 2
    icon_w, icon_h = 6, 4
    out.append(
        f'<rect x="{cx - icon_w/2:.3f}" y="{cy - icon_h:.3f}" '
        f'width="{icon_w}" height="{icon_h}" fill="none" '
        f'stroke="{r.PALETTE["gris_texto"]}" '
        f'stroke-width="{0.5 * r.MM_PER_PT:.4f}"/>'
    )
    out.append(_centered_italic(
        "Imagen disponible — completar en composición",
        x_mm=cx, y_mm=cy + 4,
        color=r.PALETTE["gris_texto"], size_pt=8,
    ))

    # Bottom-right categoría tag
    out.append(r.text(
        "18-Ficha-Cabecera-Sub",
        f"Categoría {categoria}",
        x_mm=x + w - _PLACEHOLDER_INSET_MM,
        y_mm=y + h - _PLACEHOLDER_INSET_MM,
    ))
    return out


# — Small inline SVG helpers for the placeholder internals —

def _label_start(text_str: str, x_mm: float, y_mm: float, color: str) -> str:
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
    return (
        f'<text x="{x_mm}" y="{y_mm}" '
        f'font-family="{r.font_family_css("EB Garamond")}" font-style="italic" font-weight="400" '
        f'font-size="{size_pt * r.MM_PER_PT:.4f}" '
        f'fill="{color}" text-anchor="middle">{text_str}</text>'
    )
