"""Image-zone layouts for the ficha_imagen page.

The image zone is the rectangle (col 1..6, row 3..9) — 6 reticle columns
wide × 7 rows tall. Up to 5 images are packed into it.

Each placement is a SLOT in reticle units: `(col, row, cspan, rspan)`,
1-indexed, with the row range starting at 3 (the first row the image
zone occupies — rows 1–2 carry the cabecera / tipo / title chrome). The
slot's mm geometry derives from these via `slot_mm()`.

The packer is a recursive guillotine search: for N images, try every
vertical/horizontal split of the image zone into two subzones, partition
the images between them, and recurse. At each leaf (1 image in a
subzone) pick the (cspan, rspan) ≤ subzone that best matches the
image's aspect ratio, centered inside its subzone. Score is the sum of
per-slot aspect-match × area-coverage; the best placement wins.

This replaces the previous 14-curated-layout enumeration. With ~30
slot-dimension options per image and many guillotine partitions, image
slots end up *much* closer in aspect to their images — the contain-mode
cream gap inside a slot shrinks from "obvious" to "1–3mm" in most
cases, so the visible image edges effectively follow the reticle.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]

from . import render as r
from .templates import _ficha_common as ch


# Image zone — the full reticle on the image page (cols 1..6 × rows 1..9).
# Since the v2 refactor moved all chrome to the text page, the image page
# has the entire reticle available.
IMAGE_ZONE_TOP_ROW = 1
IMAGE_ZONE_BOTTOM_ROW = 9
IMAGE_ZONE: "Zone" = (1, IMAGE_ZONE_TOP_ROW, 6, IMAGE_ZONE_BOTTOM_ROW - IMAGE_ZONE_TOP_ROW + 1)

MAX_IMAGES = 5


Slot = tuple[int, int, int, int]   # (col, row, cspan, rspan)
Zone = tuple[int, int, int, int]   # same shape; semantic name for available area
Layout = list[Slot]


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


# ── Image aspect reading ─────────────────────────────────────────────

_ASPECT_CACHE: dict[str, float] = {}
_DEFAULT_ASPECT = 1.0   # square — equally likely to fit any slot


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


# ── Packer ───────────────────────────────────────────────────────────

# Weight the per-leaf score: aspect_match ** ASPECT_EXP × area_frac.
# A higher ASPECT_EXP punishes mismatch more sharply (we'd rather use
# less of a subzone than place a portrait in a wide slot). Empirically
# 2.0 gives a decent balance — full-zone fill for matched aspects, but
# willingness to shrink slots when aspects diverge.
_ASPECT_EXP = 2.0
# Floor so that a tiny image isn't ranked alongside a full-zone one.
_AREA_FLOOR = 0.15


def _slot_aspect(cs: int, rs: int) -> float:
    w = cs * r.RETICLE_COL_W_MM + (cs - 1) * r.RETICLE_GUTTER_MM
    h = rs * r.RETICLE_ROW_H_MM + (rs - 1) * r.RETICLE_GUTTER_MM
    return w / h if h > 0 else 0.0


def _aspect_match(slot_aspect: float, img_aspect: float) -> float:
    """Symmetric ratio: 1.0 if equal, < 1 otherwise."""
    if slot_aspect <= 0 or img_aspect <= 0:
        return 0.0
    return min(slot_aspect / img_aspect, img_aspect / slot_aspect)


def _best_slot_in_zone(zone: Zone, aspect: float) -> tuple[Slot, float]:
    """Pick the (cspan, rspan) ≤ zone dims that maximizes
    aspect_match(slot, image) ** EXP × max(area_frac, FLOOR). Center the
    slot within the zone (reticle-snapped). Returns (slot, score)."""
    col, row, max_cs, max_rs = zone
    zone_area = max_cs * max_rs
    best_slot: Slot | None = None
    best_score = -1.0
    for cs in range(1, max_cs + 1):
        for rs in range(1, max_rs + 1):
            am = _aspect_match(_slot_aspect(cs, rs), aspect)
            area_frac = max((cs * rs) / zone_area, _AREA_FLOOR)
            score = (am ** _ASPECT_EXP) * area_frac
            if score > best_score:
                best_score = score
                slot_col = col + (max_cs - cs) // 2
                slot_row = row + (max_rs - rs) // 2
                best_slot = (slot_col, slot_row, cs, rs)
    assert best_slot is not None      # zone always has at least (1,1)
    return best_slot, best_score


_SEARCH_CACHE: dict[tuple[Zone, tuple[float, ...]], tuple[list[Slot], float]] = {}


def _search(zone: Zone, aspects: tuple[float, ...]) -> tuple[list[Slot], float]:
    """Recursively pack `aspects` into `zone`. Returns the placements in
    the same order as `aspects`, plus the total score.

    Memoized on (zone, sorted-rounded-aspects) — the score+placement set
    depends only on the multiset of aspects, not the input order; we map
    cached results back to the caller's order on lookup. Aspects are
    rounded to 3 decimals so visually-identical images share cache hits.
    """
    n = len(aspects)
    if n == 1:
        slot, score = _best_slot_in_zone(zone, aspects[0])
        return [slot], score

    # Cache lookup keyed on the sorted aspect multiset
    sorted_idx = sorted(range(n), key=lambda i: aspects[i])
    cache_key = (zone, tuple(round(aspects[i], 3) for i in sorted_idx))
    if cache_key in _SEARCH_CACHE:
        cached_placements, cached_score = _SEARCH_CACHE[cache_key]
        # Cached result is in sorted order; remap to input order
        result: list[Slot | None] = [None] * n
        for j, i in enumerate(sorted_idx):
            result[i] = cached_placements[j]
        return result, cached_score        # type: ignore[return-value]

    col, row, cs, rs = zone
    best_placements: list[Slot] | None = None
    best_score = -1.0

    def try_split(z1: Zone, z2: Zone) -> None:
        nonlocal best_placements, best_score
        z1_cap = z1[2] * z1[3]   # cspan * rspan = max images this subzone can hold
        z2_cap = z2[2] * z2[3]
        for k in range(1, n):
            if k > z1_cap or (n - k) > z2_cap:
                continue                # subzone can't physically hold its share
            for subset in combinations(range(n), k):
                others = tuple(i for i in range(n) if i not in subset)
                a1 = tuple(aspects[i] for i in subset)
                a2 = tuple(aspects[i] for i in others)
                p1, s1 = _search(z1, a1)
                p2, s2 = _search(z2, a2)
                total = s1 + s2
                if total > best_score:
                    best_score = total
                    result: list[Slot | None] = [None] * n
                    for j, i in enumerate(subset):
                        result[i] = p1[j]
                    for j, i in enumerate(others):
                        result[i] = p2[j]
                    best_placements = result  # type: ignore[assignment]

    # Vertical splits (split column between col+1 and col+cs-1)
    for split_col in range(col + 1, col + cs):
        z1 = (col, row, split_col - col, rs)
        z2 = (split_col, row, col + cs - split_col, rs)
        try_split(z1, z2)

    # Horizontal splits
    for split_row in range(row + 1, row + rs):
        z1 = (col, row, cs, split_row - row)
        z2 = (col, split_row, cs, row + rs - split_row)
        try_split(z1, z2)

    assert best_placements is not None

    # Cache in sorted-aspect order so multiset matches hit the cache
    sorted_placements = [best_placements[i] for i in sorted_idx]
    _SEARCH_CACHE[cache_key] = (sorted_placements, best_score)

    return best_placements, best_score


def best_layout(n_images: int, aspects: list[float]) -> Layout | None:
    """Pack `n_images` (with the given aspect ratios) into the image
    zone via guillotine search. Returns the slot for each image in
    order; or None if n is out of range / no aspects."""
    if not aspects or n_images != len(aspects) or n_images < 1 or n_images > MAX_IMAGES:
        return None
    placements, _ = _search(IMAGE_ZONE, tuple(aspects))
    return placements
