"""Flask preview server with livereload.

Renders a two-page spread at /, navigable via a left-edge slider and
arrow keys. Watches the content file, template sources, render, and
styles modules; regenerates SVGs and pushes a browser reload on change.

Run:
    python -m src.server
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory
from livereload import Server

from . import generate

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
OUT_DIR = ROOT / "out"
IMAGES_DIR = ROOT / "images"
CONTENT_FILE = ROOT / "content" / "catalog.yaml"
TEMPLATES_DIR = SRC_DIR / "templates"

app = Flask(
    __name__,
    template_folder=str(SRC_DIR / "web_templates"),
    static_folder=str(SRC_DIR / "static"),
)


def _page_ids() -> list[int]:
    catalog = generate.load_catalog()
    return sorted(p["id"] for p in catalog.get("pages", []))


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


@app.route("/")
def index():
    ids = _page_ids()
    starts = _spread_starts(ids)
    title = (generate.load_catalog().get("meta") or {}).get("title", "Catalog")
    return render_template(
        "index.html",
        page_ids=ids,
        spread_starts=starts,
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
    paths = generate.regenerate_all()
    print(f"[regen] wrote {len(paths)} pages")


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
