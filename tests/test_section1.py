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
GENERATED_SVG = ROOT / "out" / "page-006.svg"
RENDER_WIDTH_PX = 600

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
    """Re-generate page 6 from the current catalog so the test always
    compares fresh output against the reference."""
    subprocess.run(
        [sys.executable, "-m", "src.generate", "--page", "6"],
        cwd=ROOT, check=True,
    )
    assert GENERATED_SVG.exists(), f"generator did not produce {GENERATED_SVG}"
    return GENERATED_SVG


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
