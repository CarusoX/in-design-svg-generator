"""Image-zone layouts for the ficha_imagen page.

A LAYOUT is a list of SLOTs that tile the page-1 image zone (6 reticle
columns × up to 7 rows, starting at row 3). Each slot is a
`(col, row, cspan, rspan)` tuple in reticle-grid units:

    col, row    — 1-indexed top-left cell of the slot (col ∈ 1..6,
                  row ∈ 3..9 — the rows the image zone actually occupies)
    cspan       — width in cols  (≥ 1)
    rspan       — height in rows (≥ 1)

Each slot's mm geometry derives from these via _slot_mm() below so the
layouts stay independent of exact reticle dimensions.

The selector in ficha_imagen scores every candidate for the given image
count and picks the lowest-waste one.
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]

from . import render as r
from .templates import _ficha_common as ch


# Rows the image zone may occupy. Row 3 is the top because rows 1–2
# carry the cabecera, tipo eyebrow, and title.
IMAGE_ZONE_TOP_ROW = 3
IMAGE_ZONE_BOTTOM_ROW = 9


Slot = tuple[int, int, int, int]   # (col, row, cspan, rspan)
Layout = list[Slot]


# ── Candidate layouts per image count ────────────────────────────────

# 1 image — full width, height varies from 3 to 7 rows.
ONE_IMAGE: list[Layout] = [
    [(1, 3, 6, 3)],
    [(1, 3, 6, 4)],
    [(1, 3, 6, 5)],
    [(1, 3, 6, 6)],
    [(1, 3, 6, 7)],
]

# 2 images.
TWO_IMAGES: list[Layout] = [
    # A: portraits side-by-side, full height
    [(1, 3, 3, 7), (4, 3, 3, 7)],
    # B: stacked equal landscapes (rows 3+1+3=7)
    [(1, 3, 6, 3), (1, 7, 6, 3)],
    # C: big landscape on top, smaller below (rows 4+1+2=7)
    [(1, 3, 6, 4), (1, 8, 6, 2)],
]

# 3 images.
THREE_IMAGES: list[Layout] = [
    # A: three columns, full height
    [(1, 3, 2, 7), (3, 3, 2, 7), (5, 3, 2, 7)],
    # B: 1 landscape top + 2 squares below (rows 3+1+3=7)
    [(1, 3, 6, 3), (1, 7, 3, 3), (4, 7, 3, 3)],
    # C: main left + 2 stacked details right (right rows 3+1+3=7)
    [(1, 3, 4, 7), (5, 3, 2, 3), (5, 7, 2, 3)],
]

# 4 images.
FOUR_IMAGES: list[Layout] = [
    # A: 2×2 grid of 3×3 cells (rows 3+1+3=7)
    [(1, 3, 3, 3), (4, 3, 3, 3), (1, 7, 3, 3), (4, 7, 3, 3)],
    # B: 1 main top + 3 bottom row (rows 3+1+3=7)
    [(1, 3, 6, 3), (1, 7, 2, 3), (3, 7, 2, 3), (5, 7, 2, 3)],
]

# 5 images.
FIVE_IMAGES: list[Layout] = [
    # A: 2 large top + 3 small bottom (rows 4+1+2=7)
    [(1, 3, 3, 4), (4, 3, 3, 4),
     (1, 8, 2, 2), (3, 8, 2, 2), (5, 8, 2, 2)],
]


CANDIDATES: dict[int, list[Layout]] = {
    1: ONE_IMAGE,
    2: TWO_IMAGES,
    3: THREE_IMAGES,
    4: FOUR_IMAGES,
    5: FIVE_IMAGES,
}


# ── Geometry helpers ─────────────────────────────────────────────────

def slot_mm(slot: Slot) -> tuple[float, float, float, float]:
    """Convert a (col, row, cspan, rspan) slot into absolute mm
    `(x, y, w, h)` on the page. Rows are 1-indexed from the top of the
    reticle (so the image zone starts at row 3)."""
    col, row, cspan, rspan = slot
    x = ch.LEFT_X_MM + (col - 1) * (r.RETICLE_COL_W_MM + r.RETICLE_GUTTER_MM)
    y = ch.row_top(row)
    w = cspan * r.RETICLE_COL_W_MM + (cspan - 1) * r.RETICLE_GUTTER_MM
    h = rspan * r.RETICLE_ROW_H_MM + (rspan - 1) * r.RETICLE_GUTTER_MM
    return x, y, w, h


# ── Image aspect reading + layout scoring ────────────────────────────

_ASPECT_CACHE: dict[str, float] = {}
# Fallback aspect when an image can't be read (file missing, Pillow
# unavailable, etc). 1.0 = square — equally likely to fit any slot.
_DEFAULT_ASPECT = 1.0


def image_aspect(path: str, project_root: Path) -> float:
    """Width/height ratio of the image at `path` (relative to project
    root). Cached; falls back to 1.0 if Pillow is missing or the file
    can't be opened."""
    if path in _ASPECT_CACHE:
        return _ASPECT_CACHE[path]
    aspect = _DEFAULT_ASPECT
    if Image is not None:
        abs_path = (project_root / path).resolve()
        if abs_path.exists():
            try:
                with Image.open(abs_path) as im:
                    w, h = im.size
                if h > 0:
                    aspect = w / h
            except OSError:
                pass
    _ASPECT_CACHE[path] = aspect
    return aspect


def contained_size_mm(aspect: float, slot_w: float, slot_h: float) -> tuple[float, float]:
    """Largest (w, h) that preserves `aspect` (= image_w / image_h) and
    fits inside (slot_w, slot_h). The smaller of width-bound and
    height-bound wins (contain / "meet")."""
    if aspect <= 0 or slot_w <= 0 or slot_h <= 0:
        return 0.0, 0.0
    width_bound_h = slot_w / aspect
    if width_bound_h <= slot_h:
        return slot_w, width_bound_h
    return slot_h * aspect, slot_h


def layout_fill(layout: Layout, aspects: list[float]) -> float:
    """Sum of PER-SLOT fill ratios: how much of each slot the contained
    image actually fills, summed across slots. Higher = better.

    Per-slot (rather than overall slot-area-weighted) keeps a small slot
    with a perfect-fit image from being dwarfed by a big slot. Without
    that, the scorer would always pick layouts with one dominant slot
    and tiny "thumbnail" slots, because the dominant slot's high fill
    floods the overall ratio. Per-slot averaging gives matched-aspect
    image sets matched-aspect slots (e.g. two portrait images → the
    side-by-side portrait layout, not a big-portrait + thumbnail one).
    """
    score = 0.0
    for slot, aspect in zip(layout, aspects):
        _, _, w, h = slot_mm(slot)
        slot_area = w * h
        if slot_area <= 0:
            continue
        used_w, used_h = contained_size_mm(aspect, w, h)
        score += (used_w * used_h) / slot_area
    return score


def best_layout(n_images: int, aspects: list[float]) -> Layout | None:
    """Pick the candidate layout for `n_images` with the highest fill
    ratio against `aspects`. Returns None if there is no candidate
    for that count."""
    candidates = CANDIDATES.get(n_images)
    if not candidates or not aspects:
        return None
    return max(candidates, key=lambda lyt: layout_fill(lyt, aspects))
