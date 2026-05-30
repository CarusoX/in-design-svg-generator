"""Blank white page.

Used for the epigraph verso (the blank left page facing the quote) and as a
parity padder for the front matter: if `nota_curatorial` paginates to an odd
page count, the generator drops one of these in to keep the running total
before the first portadilla_sala even (so portadillas land on even/left
pages). Plain white (blanco) background; only a folio.
"""

from __future__ import annotations

from .. import render as r


def render(page_id: int, data: dict) -> str:
    return "".join([
        r.svg_open(r.PALETTE["blanco"]),
        r.folio(page_id),
        r.svg_close(),
    ])
