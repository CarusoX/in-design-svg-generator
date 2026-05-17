"""CLI: read content/catalog.yaml (section-based) and render each page to
out/page-NNN.svg.

The YAML is structured around the catalog's *sections* (portada, epigrafe,
nota_curatorial, indice, salas, bibliografia). `load_catalog()` compiles
that into a flat list of pages with sequential IDs — so removing a sala or
reordering piezas is a single YAML edit, and page numbers shift
automatically.

The compiled `{"meta": …, "pages": [{id, template, data}, …]}` shape is
kept stable so the preview server (and anything else that reads the
catalog) doesn't need to change when the YAML structure does.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import yaml

from . import templates

from . import render

ROOT = Path(__file__).resolve().parent.parent
CONTENT_FILE = ROOT / "content" / "catalog.yaml"
OUT_DIR = ROOT / "out"
RETICLE_FILE = OUT_DIR / "_reticle.svg"

# Source images live in reference/imagenes/ (authored by the curator)
# and get copied into out/images/ on each build so the entire `out/`
# folder is a self-contained InDesign handoff bundle (SVGs reference
# images via `images/<file>` relative paths).
SOURCE_IMAGES_DIR = ROOT / "reference" / "imagenes"
OUT_IMAGES_DIR = OUT_DIR / "images"


# ── Catalog loading + section → pages compilation ────────────────────

def load_catalog() -> dict:
    """Read the YAML and return {meta, pages}. Pages are computed from the
    section structure — see `_compile_pages` for the rules."""
    with CONTENT_FILE.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {
        "meta": raw.get("meta") or {},
        "pages": _compile_pages(raw),
    }


def _compile_pages(raw: dict) -> list[dict]:
    """Walk the section-based catalog and emit a flat list of pages.

    Page IDs are assigned sequentially in document order. Derivations:
      - portada.piezas / portada.salas auto-filled from the salas section
        when absent (so "57 piezas · 7 salas" stays in sync).
      - portadilla.piezas auto-filled from len(sala.piezas) when absent.
      - indice.entradas auto-filled from the salas list when absent.
      - Every ficha gets pieza_id (L001…LN, global counter across salas)
        and cabecera_sub (sala name + period) merged in — overridable per
        pieza if the YAML sets them explicitly.
    """
    salas = raw.get("salas") or []
    total_piezas = sum(len(s.get("piezas") or []) for s in salas)

    pages: list[dict] = []
    next_id = 1

    def add(template: str, data: dict) -> None:
        nonlocal next_id
        pages.append({"id": next_id, "template": template, "data": data})
        next_id += 1

    # — Portada (cover)
    if "portada" in raw:
        portada = dict(raw["portada"])
        portada.setdefault("piezas", f"{total_piezas} piezas")
        portada.setdefault("salas", f"{len(salas)} salas")
        add("portada", portada)

    # — Epígrafe
    if "epigrafe" in raw:
        add("epigrafe", dict(raw["epigrafe"]))

    # — Nota curatorial: a single body string in YAML; the template
    # paginates it dynamically (line capacity per page is computed from
    # the body style + reticle, so paragraphs flow naturally instead of
    # leaving blank space at the bottom). Pad with one blank cream page
    # if the count is odd, so the running front-matter parity
    # (portada + epigrafe + N + indice = even) keeps the first
    # portadilla_sala on an even page.
    nota_raw = raw.get("nota_curatorial")
    if nota_raw:
        from .templates.nota_curatorial import paginate as paginate_nota
        nota_pages = paginate_nota(nota_raw)
        for page_data in nota_pages:
            add("nota_curatorial", page_data)
        if len(nota_pages) % 2 == 1:
            add("blank_cream", {})

    # — Índice (auto-derive entradas if not provided). Each entry gets
    # the sala portadilla's page number, pre-computed: the índice
    # precedes the salas, so next_id+1 IS the first sala portadilla,
    # and each subsequent sala adds 2 (portadilla+blank) + 2*N piezas.
    if "indice" in raw:
        indice = dict(raw["indice"])
        sala_pages: list[int] = []
        p = next_id + 1
        for s in salas:
            sala_pages.append(p)
            p += 2 + 2 * len(s.get("piezas") or [])
        indice.setdefault("entradas", [
            {
                "romano":  s.get("romano", ""),
                "nombre":  (s.get("portadilla") or {}).get("nombre", ""),
                "periodo": (s.get("portadilla") or {}).get("periodo", ""),
                "pagina":  sala_pages[i],
            }
            for i, s in enumerate(salas)
        ])
        add("indice", indice)

    # — Salas: each one = a portadilla + N pieza spreads (imagen + texto)
    pieza_counter = 0
    for sala in salas:
        romano = sala.get("romano", "")
        sala_piezas = sala.get("piezas") or []

        # Portadilla de sala — must land on an EVEN page so it's the
        # LEFT page of a spread. The blank_red page we add right after it
        # then occupies the RIGHT page, which makes every following pieza
        # spread fall cleanly as image (even/left) + text (odd/right).
        # Each section contributes 2 + 2*N pages (always even), so once
        # the first portadilla is on an even page, every subsequent one
        # is too. If this assertion fires, adjust the front-matter
        # (nota_curatorial / indice page counts) so the running total
        # before the first portadilla ends on an odd page.
        if next_id % 2 != 0:
            raise SystemExit(
                f"portadilla_sala (sala {romano!r}) would land on odd "
                f"page {next_id} — adjust front-matter so it falls on an "
                f"even page (left of spread)."
            )

        portadilla = dict(sala.get("portadilla") or {})
        portadilla.setdefault("romano", romano)
        portadilla.setdefault("piezas", f"{len(sala_piezas)} piezas")
        add("portadilla_sala", portadilla)

        # Blank red facing page — keeps the following image/text spreads
        # aligned (image on even/left, text on odd/right).
        add("blank_red", {})

        # cabecera_sub auto-filled on every ficha in this sala
        sala_nombre = portadilla.get("nombre", "")
        sala_periodo = portadilla.get("periodo", "")
        default_cabecera = (
            f"{sala_nombre} ({sala_periodo})" if sala_nombre and sala_periodo
            else sala_nombre or sala_periodo
        )

        for pieza_idx, pieza in enumerate(sala_piezas):
            pieza_counter += 1
            default_pieza_id = pieza.get("id") or f"L{pieza_counter:03d}"

            imagen_raw = dict(pieza.get("imagen") or {})
            texto_raw = dict(pieza.get("texto") or {})

            # Text page carries the full ficha typography (title, tipo,
            # autor, datos). Those are authored under `imagen:` but
            # bridge here.
            texto = texto_raw
            texto.setdefault("pieza_id", default_pieza_id)
            texto.setdefault("cabecera_sub", default_cabecera)
            for key in ("autor", "datos", "tipo", "titulo"):
                if key in imagen_raw:
                    texto.setdefault(key, imagen_raw[key])

            imagen = imagen_raw
            imagen.setdefault("pieza_id", default_pieza_id)
            imagen.setdefault("cabecera_sub", default_cabecera)

            # Alternate the image side per pieza within the sala. The
            # first pieza puts the image on the LEFT (even page) so
            # the red expanse continues from the blank_red across the
            # spine. Subsequent piezas flip. Because each pieza spans
            # 2 pages and every back-to-back pair of red pages lies on
            # ONE physical leaf, this rhythm produces fully-red
            # leaves every other sheet through the sala.
            if pieza_idx % 2 == 0:
                add("ficha_imagen", imagen)
                add("ficha_texto", texto)
            else:
                add("ficha_texto", texto)
                add("ficha_imagen", imagen)

    # — Bibliografía
    if "bibliografia" in raw:
        add("bibliografia", dict(raw["bibliografia"]))

    return pages


# ── Rendering / writing ──────────────────────────────────────────────

def render_page(page: dict) -> str:
    template_name = page["template"]
    renderer = templates.get(template_name)
    data = dict(page.get("data") or {})
    # Surface the requested template name so the placeholder fallback can
    # show which real template still needs to be implemented.
    data["__template__"] = template_name
    return renderer(page["id"], data)


def write_page(page: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg = render_page(page)
    path = OUT_DIR / f"page-{page['id']:03d}.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def _clear_out() -> None:
    """Delete every page-*.svg in out/. Used by `regenerate_all` so that
    pages dropped from the YAML (or shifted in numbering) don't leave
    stale files behind. The reticle (_reticle.svg) is preserved because
    its filename doesn't match the page-*.svg glob."""
    if OUT_DIR.exists():
        for svg in OUT_DIR.glob("page-*.svg"):
            svg.unlink()


def write_reticle() -> Path:
    """Emit the preview-only grid overlay (out/_reticle.svg)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RETICLE_FILE.write_text(render.reticle_svg(), encoding="utf-8")
    return RETICLE_FILE


def sync_images() -> int:
    """Mirror reference/imagenes/ into out/images/ so the InDesign
    handoff bundle (just out/) contains every linked image. Skips
    files already present at the same size; returns the count copied.
    """
    if not SOURCE_IMAGES_DIR.exists():
        return 0
    OUT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in SOURCE_IMAGES_DIR.iterdir():
        if not src.is_file() or src.name.startswith("."):
            continue
        dst = OUT_IMAGES_DIR / src.name
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            continue
        shutil.copy2(src, dst)
        copied += 1
    return copied


def regenerate_all() -> list[Path]:
    catalog = load_catalog()
    _clear_out()
    paths = [write_page(p) for p in catalog["pages"]]
    write_reticle()
    sync_images()
    return paths


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate catalog SVGs.")
    parser.add_argument(
        "--page", type=int, default=None,
        help="Regenerate only the page with this id (skips the out/ cleanup).",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    pages = catalog["pages"]
    if args.page is not None:
        pages = [p for p in pages if p["id"] == args.page]
        if not pages:
            raise SystemExit(f"No page with id={args.page} in catalog.")
    else:
        _clear_out()

    for p in pages:
        path = write_page(p)
        print(f"wrote {path.relative_to(ROOT)}")

    if args.page is None:
        path = write_reticle()
        print(f"wrote {path.relative_to(ROOT)}")
        copied = sync_images()
        if copied:
            print(f"synced {copied} image(s) to {OUT_IMAGES_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
