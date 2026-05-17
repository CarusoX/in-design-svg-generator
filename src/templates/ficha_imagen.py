"""Ficha — image side (right/odd page of an artwork spread).

After the v2 refactor this page is image-only on a full rojo_tinta
background. No cabecera, no tipo, no title, no autor — those live on
the facing text page now.

All cases (1 to 5 images) dispatch through `layouts.best_layout()` —
the variable-slot guillotine packer picks each image's slot dimensions
to match its aspect ratio. For a single image that means a portrait
gets, say, a 4×9 slot centered horizontally with red breathing room on
either side, instead of being awkwardly contained inside the full
reticle. Missing source files fall back to a thin placeholder rect.
Empty `images:` (or absent key) shows the legacy proof placeholder.
Light folio at the bottom.

Expected `data` keys:
    pieza_id (str)            — for the empty-list placeholder
    images (list[str], opt.)  — relative paths (basename used)
    categoria (str)           — labels the placeholder; defaults "A"
"""

from __future__ import annotations

from pathlib import Path

from .. import layouts
from .. import render as r
from . import _ficha_common as ch


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_IMAGES_REL = "reference/imagenes"
HREF_IMAGES_DIR = "images"

# Legacy empty-list placeholder slot (kept for proofing pages with no img).
_PLACEHOLDER_SLOT: layouts.Slot = (1, 3, 6, 4)
_PLACEHOLDER_INSET_MM = 4

MAX_IMAGES = layouts.MAX_IMAGES


def render(page_id: int, data: dict) -> str:
    pieza_id = str(data.get("pieza_id", "")).strip()
    categoria = str(data.get("categoria", "A")).strip()
    images = _coerce_images(data)

    parts = [r.svg_open(r.PALETTE["rojo_tinta"])]
    parts.extend(_render_images(images, pieza_id, categoria))
    parts.append(r.folio(page_id, light=True))
    parts.append(r.svg_close())
    return "".join(parts)


def _coerce_images(data: dict) -> list[str]:
    """Read `images: [path, …]` (preferred) or single `image: "path"`
    (legacy). Returns stripped, non-empty paths."""
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
    """Place each image via best_layout() — the guillotine packer
    picks each image's slot dimensions to match its aspect ratio,
    even in the single-image case (so a portrait gets a portrait-
    shaped slot with red breathing room rather than the whole
    reticle). YAML entries are stripped to basename: aspect read
    from reference/imagenes/<file>, href emitted as images/<file>."""
    if not images:
        return _empty_placeholder(pieza_id, categoria)

    basenames = [Path(p).name for p in images]
    source_rel = [f"{SOURCE_IMAGES_REL}/{name}" for name in basenames]

    aspects = [layouts.image_aspect(p, PROJECT_ROOT) for p in source_rel]
    slots = layouts.best_layout(len(images), aspects)
    if slots is None:                    # shouldn't happen — guarded by MAX
        return _empty_placeholder(pieza_id, categoria)

    out: list[str] = []
    for name, src_rel, slot in zip(basenames, source_rel, slots):
        x, y, w, h = layouts.slot_mm(slot)
        if (PROJECT_ROOT / src_rel).exists():
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
    """The legacy proof placeholder for piezas with no image files yet.
    Stays on the red background so the visual register matches the rest
    of the page."""
    x, y, w, h = layouts.slot_mm(_PLACEHOLDER_SLOT)
    out: list[str] = [r.image_placeholder(x, y, w, h)]

    if pieza_id:
        out.append(_label_start(
            f"{pieza_id}  ·  Espacio de imagen principal",
            x_mm=x + _PLACEHOLDER_INSET_MM,
            y_mm=y + _PLACEHOLDER_INSET_MM + 2,
            color=r.PALETTE["gris_texto"],
        ))

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
