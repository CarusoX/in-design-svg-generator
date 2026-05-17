"""Flask preview server with livereload.

Renders a two-page spread at /, navigable via a left-edge slider and
arrow keys. Watches the content file, template sources, render, and
styles modules; regenerates SVGs and pushes a browser reload on change.

Run:
    python -m src.server
"""

from __future__ import annotations

import traceback
from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory
from livereload import Server

from . import generate

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
OUT_DIR = ROOT / "out"
IMAGES_DIR = OUT_DIR / "images"
CONTENT_FILE = ROOT / "content" / "catalog.yaml"
TEMPLATES_DIR = SRC_DIR / "templates"

app = Flask(
    __name__,
    template_folder=str(SRC_DIR / "web_templates"),
    static_folder=str(SRC_DIR / "static"),
)


def _spread_starts(page_ids: list[int]) -> list[int]:
    """Valid spread-start page IDs.

    Page 1 is the right-hand page of the opening spread (left side blank);
    subsequent spreads are (2, 3), (4, 5), …. Only include starts that
    correspond to at least one page actually present in the catalog.
    """
    if not page_ids:
        return []
    ids = set(page_ids)
    starts: list[int] = []
    if 1 in ids:
        starts.append(1)
    max_id = max(page_ids)
    n = 2
    while n <= max_id:
        if n in ids or (n + 1) in ids:
            starts.append(n)
        n += 2
    return starts


def _ids_on_disk() -> list[int]:
    """Page IDs that actually have a generated SVG in out/. Used as a
    fallback when the catalog YAML is mid-edit and won't parse."""
    ids: list[int] = []
    for p in OUT_DIR.glob("page-*.svg"):
        try:
            ids.append(int(p.stem.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return sorted(ids)


@app.route("/")
def index():
    # Degrade gracefully if the YAML is broken — render the index using
    # whatever SVGs are currently on disk so the preview keeps working
    # while the operator fixes the error.
    try:
        catalog = generate.load_catalog()
        ids = sorted(p["id"] for p in catalog.get("pages", []))
        title = (catalog.get("meta") or {}).get("title", "Catalog")
    except Exception:
        traceback.print_exc()
        ids = _ids_on_disk()
        title = "Catalog (catalog.yaml has an error — see terminal)"
    return render_template(
        "index.html",
        page_ids=ids,
        spread_starts=_spread_starts(ids),
        title=title,
    )


@app.route("/out/<path:filename>")
def out_file(filename: str):
    if not (OUT_DIR / filename).exists():
        abort(404)
    return send_from_directory(str(OUT_DIR), filename)


@app.route("/images/<path:filename>")
def image_file(filename: str):
    if not (IMAGES_DIR / filename).exists():
        abort(404)
    return send_from_directory(str(IMAGES_DIR), filename)


def _regenerate() -> None:
    """Regenerate every page. Swallows exceptions so a broken YAML or
    template doesn't kill the watcher — the previous good output stays on
    disk, and the next file save triggers another attempt."""
    try:
        paths = generate.regenerate_all()
        print(f"[regen] wrote {len(paths)} pages")
    except Exception:
        traceback.print_exc()
        print("[regen] FAILED — keeping last good output. Fix the error and save again.")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    _regenerate()

    server = Server(app.wsgi_app)
    server.watch(str(CONTENT_FILE), _regenerate)
    server.watch(str(TEMPLATES_DIR / "*.py"), _regenerate)
    server.watch(str(SRC_DIR / "render.py"), _regenerate)
    server.watch(str(SRC_DIR / "styles.py"), _regenerate)
    server.watch(str(IMAGES_DIR / "*"), _regenerate)
    # Preview UI: reload the browser when the HTML template changes. Flask
    # in debug mode re-reads templates per request, so no regen is needed.
    server.watch(str(SRC_DIR / "web_templates" / "*.html"))
    # The browser reload is triggered when files matched by .watch change;
    # explicitly watch the generated SVGs so a regen pushes a reload.
    server.watch(str(OUT_DIR / "*.svg"))

    server.serve(port=5050, host="127.0.0.1", debug=True, open_url_delay=None)


if __name__ == "__main__":
    main()
