"""Regression test: the generated Sala I portadilla should match the
Illustrator export the design team produced (tests/ground-truth/Section1.svg).

Strategy: render both SVGs to PNG at the same width via rsvg-convert, then
compute the mean absolute pixel difference. Tight pixel-perfect equality is
not feasible — our wrap heuristic is a character-width estimate while the
Illustrator export uses per-glyph kerning — so we assert that the average
difference is below a reasonable threshold instead. If the threshold ever
trips, dump the side-by-side composite to /tmp/section1_diff.png to inspect.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_SVG = ROOT / "tests" / "ground-truth" / "Section1.svg"
RENDER_WIDTH_PX = 600


def _sala_i_portadilla_page_id() -> int:
    """Look up which page the Sala I portadilla currently lives on —
    the page id shifts whenever front-matter (nota_curatorial pages,
    indice, etc.) grows or shrinks."""
    # Late import to avoid module-load order weirdness with the
    # templates package.
    from src.generate import load_catalog
    pages = load_catalog().get("pages", [])
    for p in pages:
        if p.get("template") == "portadilla_sala":
            data = p.get("data") or {}
            if str(data.get("romano", "")).strip() == "I":
                return p["id"]
    raise RuntimeError("No portadilla_sala page found for sala I")

# Empirically: a perfect-match render scores ~0; small per-glyph kerning
# differences between rsvg + our wrap estimate land around 5-10 (out of
# 255). 15 gives headroom while still catching real regressions (a moved
# title or wrong color easily pushes it past 30).
MAX_MEAN_DIFF = 15.0


def _have_rsvg() -> bool:
    return shutil.which("rsvg-convert") is not None


def _render(svg_path: Path, png_path: Path) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", str(RENDER_WIDTH_PX), str(svg_path), "-o", str(png_path)],
        check=True,
    )


@pytest.fixture(scope="module")
def generated_svg() -> Path:
    """Re-generate the current Sala I portadilla page so the test
    always compares fresh output against the reference, regardless of
    page-number shifts from front-matter changes."""
    page_id = _sala_i_portadilla_page_id()
    subprocess.run(
        [sys.executable, "-m", "src.generate", "--page", str(page_id)],
        cwd=ROOT, check=True,
    )
    path = ROOT / "out" / f"page-{page_id:04d}.svg"
    assert path.exists(), f"generator did not produce {path}"
    return path


@pytest.mark.skipif(not _have_rsvg(), reason="rsvg-convert not installed")
def test_sala_i_portadilla_matches_reference(generated_svg: Path, tmp_path: Path) -> None:
    mine_png = tmp_path / "mine.png"
    ref_png = tmp_path / "ref.png"
    _render(generated_svg, mine_png)
    _render(REFERENCE_SVG, ref_png)

    mine = Image.open(mine_png).convert("RGB")
    ref = Image.open(ref_png).convert("RGB")
    assert mine.size == ref.size, (
        f"render sizes differ: mine={mine.size} ref={ref.size} — both SVGs "
        f"must share the same aspect ratio (A5)"
    )

    diff = ImageChops.difference(mine, ref)
    pixels = list(diff.getdata())
    n_channels = len(pixels[0])
    total = sum(sum(p) for p in pixels)
    mean_diff = total / (len(pixels) * n_channels)

    if mean_diff > MAX_MEAN_DIFF:
        # Persist a side-by-side composite outside tmp_path so the artifact
        # survives after the test run for manual inspection.
        out = Path("/tmp/section1_diff.png")
        w, h = mine.size
        composite = Image.new("RGB", (w * 2 + 4, h), (255, 255, 255))
        composite.paste(mine, (0, 0))
        composite.paste(ref, (w + 4, 0))
        composite.save(out)
        pytest.fail(
            f"Sala I portadilla diverges from reference: mean pixel "
            f"diff = {mean_diff:.2f} (threshold {MAX_MEAN_DIFF}). "
            f"Inspect {out}"
        )
