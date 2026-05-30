"""Ficha — image side (right/odd page of an artwork spread).

After the v2 refactor this page is image-only on a full rojo_tinta
background. No cabecera, no tipo, no title, no autor — those live on
the facing text page now.

By default all 1–5 images dispatch through `layouts.best_layout()`:
the variable-slot guillotine packer picks each image's slot dimensions
to match its aspect ratio.

For piezas where the auto-pick gives the wrong arrangement, the YAML
can override per image with a `slot:` field. The packer is bypassed
ONLY when EVERY image in the list has an explicit slot — otherwise it
runs as usual (slot overrides on a subset of images would conflict
with the packer's tiling).

Image-list shapes accepted:
    images: [L005.png]                       # single string
    images:                                  # plain list
      - L005.png
      - L005-1.png
    images:                                  # explicit per-image slot
      - {file: L005-1.png, slot: [1, 1, 6, 4]}
      - {file: L005.png,   slot: [1, 5, 6, 5]}

Each `slot` is `[col, row, cspan, rspan]` in reticle units (1-indexed,
col 1..6, row 1..9 for the image page since chrome lives on the text
page). Missing source files fall back to a thin placeholder rect.
Empty `images:` (or absent key) shows the legacy proof placeholder.

Expected `data` keys:
    pieza_id (str)            — for the empty-list placeholder
    images (list, optional)   — see shapes above
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

    parts = [r.svg_open(ch.resolve_fondo(data))]
    parts.extend(_render_images(images, pieza_id, categoria))
    parts.append(r.folio(page_id, light=True))
    parts.append(r.svg_close())
    return "".join(parts)


def _coerce_images(data: dict) -> list[dict]:
    """Read `images: […]` (preferred) or single `image: "path"`
    (legacy). Each entry becomes `{file: <str>, slot: <Slot | None>}`.
    String entries get slot=None (packer assigns); dict entries with
    an explicit `slot: [col, row, cspan, rspan]` pin the placement."""
    raw = data.get("images")
    if raw is None:
        single = data.get("image")
        raw = [single] if single else []
    elif not isinstance(raw, (list, tuple)):
        raw = [raw]
    out: list[dict] = []
    for item in raw:
        if not item:
            continue
        if isinstance(item, dict):
            f = str(item.get("file", "")).strip()
            if not f:
                continue
            slot_raw = item.get("slot")
            slot = tuple(int(n) for n in slot_raw) if slot_raw else None
            # fit: "contain" (default, meet — whole image, may leave cream)
            #   or "cover" (slice — fill the slot edge-to-edge, cropping).
            fit = str(item.get("fit", "contain")).strip().lower()
            # valign / halign: where a contained image sits in its slot
            #   when it doesn't fill the slot. valign "top"|"middle"
            #   (default)|"bottom"; halign "left"|"center" (default)|"right".
            valign = str(item.get("valign", "middle")).strip().lower()
            halign = str(item.get("halign", "center")).strip().lower()
            out.append({"file": f, "slot": slot, "fit": fit,
                        "valign": valign, "halign": halign})
        else:
            s = str(item).strip()
            if s:
                out.append({"file": s, "slot": None, "fit": "contain",
                            "valign": "middle", "halign": "center"})
    if len(out) > MAX_IMAGES:
        raise ValueError(
            f"ficha_imagen supports up to {MAX_IMAGES} images, got {len(out)}"
        )
    return out


def _render_images(images: list[dict], pieza_id: str, categoria: str) -> list[str]:
    """Place each image. If EVERY entry has an explicit slot, use
    those directly (override mode). Otherwise pack via best_layout()
    using the variable-slot guillotine. Basename is stripped from
    `file`; aspect read from reference/imagenes/<file>; href emitted
    as images/<file>."""
    if not images:
        return _empty_placeholder(pieza_id, categoria)

    basenames = [Path(item["file"]).name for item in images]
    source_rel = [f"{SOURCE_IMAGES_REL}/{name}" for name in basenames]

    if all(item["slot"] is not None for item in images):
        slots = [item["slot"] for item in images]
    else:
        aspects = [layouts.image_aspect(p, PROJECT_ROOT) for p in source_rel]
        slots = layouts.best_layout(len(images), aspects)
        if slots is None:                # shouldn't happen — guarded by MAX
            return _empty_placeholder(pieza_id, categoria)

    fits = [item.get("fit", "contain") for item in images]
    valigns = [item.get("valign", "middle") for item in images]
    haligns = [item.get("halign", "center") for item in images]
    _Y = {"top": "Min", "middle": "Mid", "bottom": "Max"}
    _X = {"left": "Min", "center": "Mid", "right": "Max"}
    out: list[str] = []
    for name, src_rel, slot, fit, valign, halign in zip(
        basenames, source_rel, slots, fits, valigns, haligns
    ):
        x, y, w, h = layouts.slot_mm(slot)
        if (PROJECT_ROOT / src_rel).exists():
            href = f"{HREF_IMAGES_DIR}/{name}"
            # "slice" scales to cover and clips to the image's own viewport
            # (the x/y/width/height box); "meet" contains the whole image.
            # The X/Y tokens set where a contained image sits in its slot.
            mode = "slice" if fit == "cover" else "meet"
            par = f"x{_X.get(halign, 'Mid')}Y{_Y.get(valign, 'Mid')} {mode}"
            out.append(
                f'<image x="{x:.4f}" y="{y:.4f}" '
                f'width="{w:.4f}" height="{h:.4f}" '
                f'href="{href}" preserveAspectRatio="{par}"/>'
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
