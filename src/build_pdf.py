"""Build `out/catalog.pdf` from the per-page SVGs in `out/`.

Each PDF page is A4 landscape (297×210 mm) with the spread's two A5
pages placed side by side, mirroring what the preview server shows in
the browser. Page 1 sits alone on the right of the opening spread
(blank facing); subsequent spreads pair (2,3), (4,5), …; the final
spread may be a single page on the left if the catalog ends on an
even page.

Pipeline:
1. For each spread, build a composite A4-landscape SVG that nests the
   two A5 page SVGs as inline `<svg>` children at the correct x/y.
   The composite is written into `out/` so the page SVGs' relative
   `<image href="images/…">` references still resolve (the images live
   in `out/images/`, already synced by `src.generate.sync_images`).
2. `rsvg-convert -f pdf` renders each composite to a single-page PDF
   in a temp directory; the composite SVGs are cleaned up after.
3. `pdfunite` concatenates the per-spread PDFs into `out/catalog.pdf`.

Requires `rsvg-convert` (librsvg) and `pdfunite` (poppler-utils).
Install via Homebrew: `brew install librsvg poppler`.

Run:
    python -m src.build_pdf
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"
VENDOR_FONTS_DIR = ROOT / "vendor" / "fonts"
DEFAULT_PDF_OUT = OUT_DIR / "catalog.pdf"

# Spread sheet = two A5 portraits flush side by side. We deliberately
# do NOT center inside a 297×210 A4 frame anymore — the 0.5mm of slack
# on each outer edge rendered as a white strip on rojo_tinta pages,
# which read as "noise" against the red bleed. 296×210 is 1mm
# narrower than true A4 but every consumer printer auto-scales /
# centers the page anyway, so the print proof is unaffected.
A5_W_MM = 148
A5_H_MM = 210
SPREAD_W_MM = 2 * A5_W_MM                                   # 296
SPREAD_H_MM = A5_H_MM                                       # 210
LEFT_PAGE_X_MM = 0                                          # flush left
RIGHT_PAGE_X_MM = A5_W_MM                                   # flush against the spine


def _inner_svg(svg_path: Path) -> str:
    """Strip the outer `<svg …>` and closing `</svg>` of a per-page
    SVG and return just the inner markup, ready to be inlined inside a
    composite `<svg>` with its own viewBox."""
    text = svg_path.read_text(encoding="utf-8")
    open_tag_end = text.find(">", text.find("<svg")) + 1
    close_tag_start = text.rfind("</svg>")
    return text[open_tag_end:close_tag_start]


def composite_spread_svg(
    left_path: Path | None, right_path: Path | None,
) -> str:
    """Build an A4-landscape SVG with the spread's left/right A5 pages
    embedded as nested `<svg>` children. A page is omitted when its
    path is None (opening spread → left=None; trailing spread when the
    catalog ends on an even page → right=None)."""
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{SPREAD_W_MM}mm" height="{SPREAD_H_MM}mm" '
        f'viewBox="0 0 {SPREAD_W_MM} {SPREAD_H_MM}">',
        # White paper background — anything not covered by a page reads
        # as the sheet itself. With pages flush to both outer edges,
        # this only shows on the opening / closing spread where one
        # side is intentionally blank.
        f'<rect width="{SPREAD_W_MM}" height="{SPREAD_H_MM}" fill="white"/>',
    ]
    if left_path is not None:
        parts.append(
            f'<svg x="{LEFT_PAGE_X_MM}" y="0" '
            f'width="{A5_W_MM}" height="{A5_H_MM}" '
            f'viewBox="0 0 {A5_W_MM} {A5_H_MM}">'
            f"{_inner_svg(left_path)}"
            "</svg>"
        )
    if right_path is not None:
        parts.append(
            f'<svg x="{RIGHT_PAGE_X_MM}" y="0" '
            f'width="{A5_W_MM}" height="{A5_H_MM}" '
            f'viewBox="0 0 {A5_W_MM} {A5_H_MM}">'
            f"{_inner_svg(right_path)}"
            "</svg>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _build_spreads(
    page_paths: dict[int, Path],
) -> list[tuple[Path | None, Path | None]]:
    """Mirror `src.server._spread_starts`: opening spread = (blank, page-1);
    subsequent spreads pair (2,3), (4,5), …; a final lone even page lands
    alone on the left of its spread."""
    if not page_paths:
        return []
    spreads: list[tuple[Path | None, Path | None]] = []
    if 1 in page_paths:
        spreads.append((None, page_paths[1]))
    max_id = max(page_paths)
    p = 2
    while p <= max_id:
        left = page_paths.get(p)
        right = page_paths.get(p + 1)
        if left is not None or right is not None:
            spreads.append((left, right))
        p += 2
    return spreads


def _write_fontconfig(tmp_dir: Path) -> Path:
    """Write a self-contained fontconfig: the vendored Google variable EB
    Garamond FIRST, then the system font directories, listed EXPLICITLY —
    deliberately NOT `<include>`-ing the system `fonts.conf`.

    Why pin the vendored EB Garamond: rsvg's default (CoreText) backend
    picks the locally installed optical cuts EBGaramond12/08 for
    "EB Garamond", whose glyphs differ from the Google variable family
    our wrap was calibrated against — most visibly the cap-Q swash, whose
    long tail overruns the next letters ("Quedan"). The vendored variable
    (what the browser preview also loads) keeps the Q contained. Listing
    its `<dir>` first makes it win the family-name match.

    Why explicit dirs instead of `<include>`: on some macOS + Homebrew
    setups the bundled `fonts.conf` / conf.d leaves the matcher broken —
    `fc-match` returns a single CJK fallback ('Hiragino Sans') for EVERY
    family. Scanning the directories directly (no conf.d) sidesteps that:
    EB Garamond resolves to the vendored variable and Lato / Caveat to
    their installed files. `_font_pinning_works` re-checks this at build
    time and falls back to CoreText if it ever fails."""
    home_fonts = Path.home() / "Library" / "Fonts"
    conf = textwrap.dedent(f"""\
        <?xml version="1.0"?>
        <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
        <fontconfig>
          <dir>{VENDOR_FONTS_DIR}</dir>
          <dir>{home_fonts}</dir>
          <dir>/System/Library/Fonts</dir>
          <dir>/System/Library/Fonts/Supplemental</dir>
          <dir>/Library/Fonts</dir>
          <cachedir>{tmp_dir / "fc-cache"}</cachedir>
        </fontconfig>
    """)
    path = tmp_dir / "fontconfig.conf"
    path.write_text(conf, encoding="utf-8")
    return path


def _rsvg_env(fontconfig_path: Path) -> dict[str, str]:
    """Env for rsvg-convert that pins font selection to our vendored
    EB Garamond variable family.

    Two pieces matter, both required:
    - `PANGOCAIRO_BACKEND=fc` forces Pango (which librsvg uses to lay
      out text) to use its fontconfig backend instead of the macOS
      CoreText backend. CoreText doesn't honour FONTCONFIG_FILE, so
      without this the override is silently ignored on Mac.
    - `FONTCONFIG_FILE` points at the temp config from
      `_write_fontconfig`, which adds `vendor/fonts/` to fontconfig's
      search path so our Google variable TTFs win the family match."""
    return {
        **os.environ,
        "PANGOCAIRO_BACKEND": "fc",
        "FONTCONFIG_FILE": str(fontconfig_path),
    }


def _font_pinning_works(env: dict[str, str]) -> bool:
    """True only if fontconfig (under `env`) actually resolves
    'EB Garamond' to a Garamond face.

    The font-pinning env above routes text layout through Pango's
    fontconfig backend. That's the right path when fontconfig is healthy.
    But on some macOS + Homebrew setups the fontconfig matcher is broken
    at the library level: `fc-match` returns a single system fallback
    (observed: 'Hiragino Sans') for EVERY family, even when `fc-list`
    clearly contains Lato / EB Garamond. The PDF then embeds the wrong
    faces (Hiragino for Lato, PT Serif for EB Garamond) and the wider
    fallback overflows / clips the text.

    When we detect that, we skip the env and let rsvg use its DEFAULT
    backend — CoreText on macOS — which reads the installed fonts
    (~/Library/Fonts etc.) directly and embeds the real Lato + EB
    Garamond. (Install the fonts with `brew install --cask font-lato
    font-eb-garamond font-caveat`.)"""
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{family}", "EB Garamond"],
            capture_output=True, text=True, env=env, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return False
    return "garamond" in out.lower()


def _collect_pages() -> dict[int, Path]:
    out: dict[int, Path] = {}
    for path in OUT_DIR.glob("page-*.svg"):
        stem_id = path.stem.split("-", 1)[1]
        if stem_id.isdigit():
            out[int(stem_id)] = path
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build catalog.pdf from out/page-*.svg.",
    )
    parser.add_argument(
        "-o", "--output", default=str(DEFAULT_PDF_OUT),
        help=f"PDF output path (default: {DEFAULT_PDF_OUT})",
    )
    args = parser.parse_args()

    for cmd in ("rsvg-convert", "pdfunite"):
        if shutil.which(cmd) is None:
            raise SystemExit(
                f"Missing {cmd!r} — install librsvg + poppler "
                f"(`brew install librsvg poppler`)."
            )

    page_paths = _collect_pages()
    if not page_paths:
        raise SystemExit(
            "No page-*.svg files in out/. "
            "Run `python -m src.generate` first."
        )

    spreads = _build_spreads(page_paths)
    output_pdf = Path(args.output)

    # Composite SVGs are written into out/ so the embedded pages'
    # relative `<image href="images/…">` references still resolve. They
    # are cleaned up after each spread renders.
    composite_paths: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        rsvg_env = _rsvg_env(_write_fontconfig(tmp))
        if not _font_pinning_works(rsvg_env):
            # fontconfig matcher broken on this machine — it would embed
            # the wrong faces (Hiragino / PT Serif) and clip the text.
            # Use rsvg's native CoreText backend instead, which embeds the
            # real installed Lato + EB Garamond.
            print(
                "note: fontconfig can't match the catalog fonts here; using "
                "the native CoreText backend (embeds the installed Lato + "
                "EB Garamond directly)."
            )
            rsvg_env = None
        spread_pdfs: list[Path] = []
        try:
            for idx, (left, right) in enumerate(spreads):
                svg_path = OUT_DIR / f"_spread_{idx:03d}.svg"
                svg_path.write_text(
                    composite_spread_svg(left, right), encoding="utf-8",
                )
                composite_paths.append(svg_path)

                pdf_path = tmp / f"spread_{idx:03d}.pdf"
                subprocess.run(
                    [
                        "rsvg-convert", "-f", "pdf",
                        "-o", str(pdf_path), str(svg_path),
                    ],
                    check=True, env=rsvg_env,
                )
                spread_pdfs.append(pdf_path)

            subprocess.run(
                ["pdfunite", *[str(p) for p in spread_pdfs], str(output_pdf)],
                check=True,
            )
        finally:
            for svg_path in composite_paths:
                svg_path.unlink(missing_ok=True)

    rel = output_pdf.relative_to(ROOT) if output_pdf.is_relative_to(ROOT) else output_pdf
    print(
        f"wrote {rel}  ({len(spreads)} spreads, {len(page_paths)} pages)"
    )


if __name__ == "__main__":
    main()
