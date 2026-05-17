"""Blank red page — the right-facing companion to a portadilla.

Auto-inserted after every portadilla_sala by `generate._compile_pages` so
each artwork that follows lands on a fresh spread (image on the even/left
page, text on the odd/right page). No content beyond the page color and
the folio.
"""

from __future__ import annotations

from .. import render as r


def render(page_id: int, data: dict) -> str:
    return "".join([
        r.svg_open(r.PALETTE["rojo_tinta"]),
        r.folio(page_id, light=True),
        r.svg_close(),
    ])
