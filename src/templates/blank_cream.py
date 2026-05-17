"""Blank cream page — parity padder for the front matter.

If `nota_curatorial` paginates to an odd page count, the generator drops
one of these in to keep the running total before the first portadilla_sala
even (so portadillas land on even/left pages).
"""

from __future__ import annotations

from .. import render as r


def render(page_id: int, data: dict) -> str:
    return "".join([
        r.svg_open(r.PALETTE["papel_crema"]),
        r.folio(page_id),
        r.svg_close(),
    ])
