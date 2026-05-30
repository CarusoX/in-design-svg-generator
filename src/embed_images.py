"""Emit `page-NNNN-embedded.svg` variants with raster images inlined
as base64 data URIs.

Reason: Illustrator / Affinity Designer often fail to resolve a SVG's
`<image href="images/foo.jpg">` against the file system when the SVG
is *imported* (vs. opened in place). The embedded variant carries the
pixels inside the SVG document, so it loads as a single self-contained
file — at the cost of file size, since base64 inflates each image
~33% and prevents the apps from sharing or re-linking them later.

Use this for one-off Illustrator sessions; the regular per-page SVGs
in `out/` keep the linked images for the InDesign handoff (which DOES
resolve relative `href`s correctly).

Usage:
    python -m src.embed_images 5 21 82
    # → out/page-0005-embedded.svg, page-0021-embedded.svg, …
"""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}

# Match `href="images/foo.ext"` or `xlink:href="images/foo.ext"` on an <image>.
_HREF_RE = re.compile(r'((?:xlink:)?href)="(images/[^"]+)"')


def embed_images(svg_path: Path) -> tuple[str, int]:
    """Return (new_svg_text, count_embedded). The output is tweaked for
    Illustrator / Affinity Designer compatibility:

    1. Each `<image>` reference is rewritten to `xlink:href="data:…"`.
       SVG 1.1 (the dialect those apps support) only recognises the
       `xlink:href` attribute on `<image>` — bare `href` (SVG 2) is
       silently ignored, which is why the original linked-image
       version refused to load.
    2. `xmlns:xlink="http://www.w3.org/1999/xlink"` is injected into
       the root `<svg>` if it's missing, otherwise the `xlink:` prefix
       above is unbound and the SVG fails XML validation.

    Missing image files on disk are left untouched in the markup so
    the operator can spot which reference broke."""
    text = svg_path.read_text(encoding="utf-8")
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        rel = match.group(2)
        img_path = OUT_DIR / rel
        if not img_path.exists():
            return match.group(0)
        mime = _MIME_BY_SUFFIX.get(
            img_path.suffix.lower(), "application/octet-stream",
        )
        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        count += 1
        return f'xlink:href="data:{mime};base64,{data}"'

    text = _HREF_RE.sub(repl, text)
    if 'xmlns:xlink' not in text:
        text = text.replace(
            'xmlns="http://www.w3.org/2000/svg"',
            'xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"',
            1,
        )
    return text, count


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Embed referenced raster images into page SVGs so they "
            "open as self-contained files in Illustrator / Designer."
        ),
    )
    parser.add_argument(
        "pages", nargs="+", type=int,
        help="Page IDs to embed (e.g. 5 21 82).",
    )
    args = parser.parse_args()

    for pid in args.pages:
        src = OUT_DIR / f"page-{pid:03d}.svg"
        if not src.exists():
            print(f"!! missing {src.name}")
            continue
        new_text, n = embed_images(src)
        dst = OUT_DIR / f"page-{pid:03d}-embedded.svg"
        dst.write_text(new_text, encoding="utf-8")
        kb = dst.stat().st_size / 1024
        print(f"wrote {dst.name}  ({n} image(s) embedded, {kb:.1f} KB)")


if __name__ == "__main__":
    main()
