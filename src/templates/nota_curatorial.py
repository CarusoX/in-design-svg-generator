"""Nota curatorial — cream-paper essay pages with index-style title.

Layout:
- Same title treatment as the índice: red Lato Black 22pt
  ("Indice-Titulo" style) anchored with its FIRST baseline at the bottom
  of cell (row 1, col 1). The title overflows downward into row 2 when
  it wraps. Title only renders on the first page; subsequent pages set
  `is_continuation: true` and skip the title.
- Body in EB Garamond Regular 10/15.5, left-aligned with hyphenation.
  Bibliographic references in parentheses are auto-italicized (see
  `_REF_PATTERN`).
- Paragraphs split on blank lines. Every paragraph gets a 5mm
  first-line indent (sangría) — but a paragraph that continues from
  the previous page (split mid-paragraph by the paginator) does NOT
  get an indent on its first line; it just keeps reading.
- Body starts:
    - First page: row 3 top (cap-top of first line on row 3 top)
    - Continuation pages: row 1 top
- Folio in the outer margin.

`paginate()` is the entry point — it splits a single curatorial note
(dict `{titulo, body}`) into a sequence of per-page `data` dicts that
`render()` consumes. Pages are filled line-by-line; paragraphs that
overflow are split at line boundaries so no whitespace is wasted at
the bottom of a page.

Per-page `data` shape (produced by `paginate`, consumed by `render`):
    titulo (str, optional)           — first page only
    is_continuation (bool, optional) — every page after the first
    segments (list[dict])            — contiguous chunks of pre-wrapped
        lines (one segment per paragraph-region on the page).
        Each item:
            {"lines": [[ (text, italic), ... ], ...], "indent": bool}
        Each line is a list of (text, italic) runs ready to be emitted
        as alternating `<tspan>`s. `indent` is True only when the
        segment is the START of a paragraph (gets the 5mm first-line
        sangría); False when the segment is the tail of a paragraph
        that began on the previous page.
"""

from __future__ import annotations

import re
from dataclasses import replace
from xml.sax.saxutils import escape

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


_GARAMOND_CAP_RATIO = 0.685

# Title position (first page only): same as índice page. FIRST line's
# baseline sits at row_bottom(1); subsequent wrapped lines stack downward
# into row 2.
TITLE_X_MM = ch.LEFT_X_MM
TITLE_MAX_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM
TITLE_FIRST_BASELINE_Y_MM = ch.row_bottom(1)
_TITLE_STYLE = TEXT_STYLES["Indice-Titulo"]

# Body geometry: full reticle width, starts on row 3 (first page) or
# row 1 (continuation pages). First baseline = row_top + cap_h so the
# first line's cap-top sits on the row's top edge.
BODY_X_MM = ch.LEFT_X_MM
BODY_MAX_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM
_BODY_STYLE_ID = "09-Body-Garamond"
_BODY_STYLE = TEXT_STYLES[_BODY_STYLE_ID]
# Italic-equivalent body style — same family/size, italic on. Used both
# for italic-run width measurement during wrap, and to emit references
# inline as `<tspan font-style="italic">`.
_BODY_ITALIC_STYLE = replace(_BODY_STYLE, font_style="italic")
_BODY_CAP_H_MM = _GARAMOND_CAP_RATIO * _BODY_STYLE.size_pt * r.MM_PER_PT
_BODY_LEADING_MM = (
    (_BODY_STYLE.leading_pt or _BODY_STYLE.size_pt * 1.2) * r.MM_PER_PT
)
_BODY_DESC_MM = 0.21 * _BODY_STYLE.size_pt * r.MM_PER_PT

# Closing colophon — italic, fixed at 10pt (the body size before the
# 12pt bump). Smaller than the body so it reads as a separate "note".
# Anchored with its cap-top on the top edge of row 8 (fixed slot,
# regardless of how much body sits above), so the closing note always
# lands in the same spot on the page.
_COLOPHON_STYLE = replace(
    _BODY_STYLE, font_style="italic", size_pt=10, leading_pt=15.5,
)
_COLOPHON_CAP_H_MM = _GARAMOND_CAP_RATIO * _COLOPHON_STYLE.size_pt * r.MM_PER_PT
_COLOPHON_LEADING_MM = (
    (_COLOPHON_STYLE.leading_pt or _COLOPHON_STYLE.size_pt * 1.2) * r.MM_PER_PT
)
_COLOPHON_DESC_MM = 0.21 * _COLOPHON_STYLE.size_pt * r.MM_PER_PT
_COLOPHON_CAP_TOP_Y_MM = ch.row_top(8)
_COLOPHON_FIRST_BASELINE_Y_MM = _COLOPHON_CAP_TOP_Y_MM + _COLOPHON_CAP_H_MM
# Visual gap between regular body (above) and colophon (below). 8mm ≈
# one body-line-and-change of breathing room so the two read as
# separate blocks rather than one continuous paragraph.
_COLOPHON_GAP_MM = 8.0

PARA_INDENT_MM = 5

# Body first-baseline positions:
#   - First page: cap-top of line 1 sits on the top of row 3 (the title
#     occupies row 1 / spills into row 2).
#   - Continuation pages: baseline of line 1 sits at the bottom of row 1,
#     mirroring how the title is anchored on the first page. This pushes
#     the body down by ~one row, giving every page the same visual
#     "header band" of empty space at the top.
_FIRST_PAGE_FIRST_BASELINE_Y_MM = ch.row_top(3) + _BODY_CAP_H_MM
_CONT_PAGE_FIRST_BASELINE_Y_MM = ch.row_bottom(1)

# Vertical budget per page = (bottom of row 9) − (first baseline) − descender.
# Lines fit when (N - 1) * leading + descender ≤ budget, so:
#     N ≤ 1 + (budget) / leading.
_PAGE_BOTTOM_Y_MM = ch.row_bottom(9)


def _line_capacity(first_baseline_y_mm: float) -> int:
    budget = _PAGE_BOTTOM_Y_MM - first_baseline_y_mm - _BODY_DESC_MM
    return max(1, 1 + int(budget // _BODY_LEADING_MM))


FIRST_PAGE_LINE_CAPACITY = _line_capacity(_FIRST_PAGE_FIRST_BASELINE_Y_MM)
CONT_PAGE_LINE_CAPACITY = _line_capacity(_CONT_PAGE_FIRST_BASELINE_Y_MM)


# ── Reference detection (auto-italic) ────────────────────────────────
# Bibliographic references in this essay are all parenthetical and
# contain a 4-digit year (e.g. "(Chartier, R., 2006, p. 55)",
# "(Valdés de León, 2008)"). The body has no non-reference parens, so
# matching any parens that contain a year safely italicizes every
# citation without false positives.
_REF_PATTERN = re.compile(r"\([^)]*\b\d{4}\b[^)]*\)")


def _tokenize_italics(paragraph: str) -> list[tuple[str, bool]]:
    """Split a paragraph into (word, italic) tuples. A word is marked
    italic when ANY character of it falls within a reference span."""
    ranges = [(m.start(), m.end()) for m in _REF_PATTERN.finditer(paragraph)]

    def overlaps(start: int, end: int) -> bool:
        for rs, re_ in ranges:
            if start < re_ and end > rs:
                return True
        return False

    out: list[tuple[str, bool]] = []
    for m in re.finditer(r"\S+", paragraph):
        out.append((m.group(), overlaps(m.start(), m.end())))
    return out


# ── Rich word wrap (italic-aware, hyphenation-aware) ─────────────────

def _wrap_rich(
    words: list[tuple[str, bool]], max_w_mm: float,
    first_line_indent_mm: float = 0.0,
    base_style=None, italic_style=None,
) -> list[list[tuple[str, bool]]]:
    """Greedy wrap of italic-tagged words. Mirrors r.wrap_lines, but
    measures each word's width with the matching (regular/italic) style
    and preserves the italic flag on hyphenation fragments.

    `first_line_indent_mm` shrinks the available width for the FIRST
    line only (the rest get the full `max_w_mm`). Necessary because
    paragraphs here get a 5mm sangría on the first line — without
    subtracting it from the first line's wrap budget the line packs to
    the full reticle width and the rendered text spills 5mm past the
    right edge.

    `base_style` / `italic_style` default to the body's 12pt regular /
    italic styles. The colophon overrides both to a 10pt italic style so
    its measurements (and emitted font-size) match what render emits.

    Space measurement matters: every inter-word space ends up inside the
    tspan of the word that FOLLOWS it (within a same-italic run it's
    part of the run's " ".join(); across runs it's the leading character
    of the next run's tspan). So the space's font style equals the
    following word's style."""
    base_style = base_style if base_style is not None else _BODY_STYLE
    italic_style = italic_style if italic_style is not None else _BODY_ITALIC_STYLE
    lines: list[list[tuple[str, bool]]] = []
    current: list[tuple[str, bool]] = []
    current_w_mm = 0.0
    current_max_mm = max(1.0, max_w_mm - first_line_indent_mm)
    for word, italic in words:
        word_style = italic_style if italic else base_style
        word_w_mm = r._measure_word_mm(word, word_style)
        space_mm = r._measure_word_mm(" ", word_style) if current else 0.0
        added_w_mm = word_w_mm + space_mm
        if current and current_w_mm + added_w_mm > current_max_mm:
            space_for_prefix_mm = current_max_mm - current_w_mm - space_mm
            broken = r._hyphen_break_word(word, space_for_prefix_mm, word_style)
            if broken is not None:
                prefix, suffix = broken
                current.append((prefix + "-", italic))
                lines.append(current)
                current = [(suffix, italic)]
                current_w_mm = r._measure_word_mm(suffix, word_style)
                current_max_mm = max_w_mm
                continue
            lines.append(current)
            current = [(word, italic)]
            current_w_mm = word_w_mm
            current_max_mm = max_w_mm
        else:
            current.append((word, italic))
            current_w_mm += added_w_mm
    if current:
        lines.append(current)
    return lines


def _coalesce_runs(line: list[tuple[str, bool]]) -> list[tuple[str, bool]]:
    """Merge consecutive same-italic words into one run, joined by spaces."""
    if not line:
        return []
    runs: list[list] = [[[line[0][0]], line[0][1]]]
    for word, italic in line[1:]:
        if italic == runs[-1][1]:
            runs[-1][0].append(word)
        else:
            runs.append([[word], italic])
    return [(" ".join(words), italic) for words, italic in runs]


# ── Pagination ───────────────────────────────────────────────────────

def paginate(note: dict, colophon: bool = True) -> list[dict]:
    """Split a curatorial note's body across pages, filling each page
    line-by-line. When a paragraph doesn't fit, top-up the current page
    with as many of its lines as fit and continue the rest on the next
    page (with no first-line indent, since it's not a new paragraph).

    `colophon=True` (the opening nota) renders the LAST paragraph as a
    fully-italic closing note anchored to row 8. Set `colophon=False`
    (e.g. the closing essay / acknowledgments) to flow every paragraph
    as regular body, with no italic colophon."""
    titulo = str(note.get("titulo", "")).strip()
    body = str(note.get("body", "")).strip()
    if not body:
        return [{"titulo": titulo}] if titulo else []

    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    # The final paragraph can be a colophon: rendered fully italic and
    # anchored to the bottom of its page. Everything else flows from the
    # top. With colophon=False, no paragraph is peeled off.
    if colophon:
        colophon_text = paragraphs[-1] if len(paragraphs) >= 1 else ""
        regular_paragraphs = paragraphs[:-1]
    else:
        colophon_text = ""
        regular_paragraphs = paragraphs

    # Pre-wrap every regular paragraph. The first line gets a narrower
    # budget to leave room for the 5mm sangría; the rest use the full
    # reticle width. Each line is a list of runs ready for emission
    # (consecutive same-italic words coalesced).
    paragraph_lines: list[list[list[tuple[str, bool]]]] = []
    for para in regular_paragraphs:
        words = _tokenize_italics(para)
        wrapped = _wrap_rich(
            words, BODY_MAX_W_MM,
            first_line_indent_mm=PARA_INDENT_MM,
        )
        paragraph_lines.append([_coalesce_runs(line) for line in wrapped])

    # Colophon: every word forced italic, no first-line sangría (it sits
    # on its own at the bottom; an indent would read as a regular ¶).
    # Uses the smaller 10pt colophon style for both wrap and emission.
    colophon_lines: list[list[tuple[str, bool]]] = []
    if colophon_text:
        colo_words = [(m.group(), True) for m in re.finditer(r"\S+", colophon_text)]
        wrapped = _wrap_rich(
            colo_words, BODY_MAX_W_MM,
            base_style=_COLOPHON_STYLE, italic_style=_COLOPHON_STYLE,
        )
        colophon_lines = [_coalesce_runs(line) for line in wrapped]

    pages: list[dict] = []
    cur_segments: list[dict] = []
    cur_used = 0

    def cap() -> int:
        return CONT_PAGE_LINE_CAPACITY if pages else FIRST_PAGE_LINE_CAPACITY

    def flush() -> None:
        nonlocal cur_segments, cur_used
        if not cur_segments:
            return
        page: dict = {"segments": cur_segments}
        if pages:
            page["is_continuation"] = True
        elif titulo:
            page["titulo"] = titulo
        pages.append(page)
        cur_segments = []
        cur_used = 0

    for lines in paragraph_lines:
        # First chunk of every paragraph gets the indent; later chunks
        # (when the paragraph spills onto a new page) do not.
        is_paragraph_start = True
        remaining = list(lines)
        while remaining:
            available = cap() - cur_used
            if available <= 0:
                flush()
                continue
            take = remaining[:available]
            remaining = remaining[available:]
            cur_segments.append({"lines": take, "indent": is_paragraph_start})
            cur_used += len(take)
            is_paragraph_start = False
            if remaining:
                flush()
    flush()

    # Attach the colophon. It anchors with its cap-top on the top of
    # row 7 (fixed position), so the fit check is just: does the body
    # bottom — plus _COLOPHON_GAP_MM of breathing room — still sit
    # above the colophon's cap-top? Otherwise push the colophon to a
    # fresh page (where it occupies the same row-7 slot alone).
    if colophon_lines:
        if pages:
            last_page = pages[-1]
            last_used = sum(len(s["lines"]) for s in last_page["segments"])
            body_first_baseline = (
                _FIRST_PAGE_FIRST_BASELINE_Y_MM if len(pages) == 1
                else _CONT_PAGE_FIRST_BASELINE_Y_MM
            )
            body_bottom_y = (
                body_first_baseline
                + (last_used - 1) * _BODY_LEADING_MM
                + _BODY_DESC_MM
            )
            if body_bottom_y + _COLOPHON_GAP_MM <= _COLOPHON_CAP_TOP_Y_MM:
                last_page["colophon"] = colophon_lines
            else:
                pages.append({
                    "is_continuation": True,
                    "colophon": colophon_lines,
                })
        else:
            # No regular body — colophon is the whole note. Keep the
            # title with it so the first-page chrome still appears.
            page: dict = {"colophon": colophon_lines}
            if titulo:
                page["titulo"] = titulo
            pages.append(page)

    return pages


# ── Rendering ────────────────────────────────────────────────────────

def _line_attrs_for(style) -> str:
    """`<text>` presentation attributes for `style` — used so each line
    can choose its own font-size while individual `<tspan>` children
    still only need to override font-style for italic runs."""
    fill = r.PALETTE[style.color]
    size_mm = style.size_pt * r.MM_PER_PT
    return (
        f'font-family="{r.font_family_css(style.font_family, style.font_weight)}" '
        f'font-size="{size_mm:.4f}" font-weight="{style.font_weight}" '
        f'fill="{fill}" text-anchor="{style.align}"'
    )


_BODY_LINE_ATTRS = _line_attrs_for(_BODY_STYLE)
_COLOPHON_LINE_ATTRS = _line_attrs_for(_COLOPHON_STYLE)


def _emit_runs_line(
    runs: list[tuple[str, bool]], x_mm: float, y_mm: float,
    attrs: str = _BODY_LINE_ATTRS,
) -> str:
    """Emit one wrapped line as a `<text>` whose `<tspan>` children
    alternate between regular and italic. Subsequent tspans omit `x`
    so they flow horizontally from where the previous one ended;
    inter-run spaces are inserted into the leading edge of each run
    after the first."""
    if not runs:
        return ""
    parts = [
        f'<text xml:space="preserve" x="{x_mm}" y="{y_mm}" '
        f'{attrs}>'
    ]
    for i, (text, italic) in enumerate(runs):
        # Restore the space between runs (it was the separator between
        # the last word of the previous run and the first word of this
        # one — stripped when we coalesced).
        chunk = text if i == 0 else " " + text
        if italic:
            parts.append(f'<tspan font-style="italic">{escape(chunk)}</tspan>')
        else:
            parts.append(f'<tspan>{escape(chunk)}</tspan>')
    parts.append('</text>')
    return "".join(parts)


def _emit_segment(
    lines: list[list[tuple[str, bool]]],
    y_first_baseline: float,
    indent_first: bool,
    leading_mm: float = _BODY_LEADING_MM,
    attrs: str = _BODY_LINE_ATTRS,
) -> str:
    """Render a contiguous run of pre-wrapped lines. `y_first_baseline`
    is the baseline of the first line. When `indent_first` is True the
    first line is offset by PARA_INDENT_MM; subsequent lines sit flush
    at BODY_X_MM. `leading_mm` + `attrs` default to the body style;
    callers (the colophon) override both for its 10pt italic emission."""
    indent_mm = PARA_INDENT_MM if indent_first else 0
    parts: list[str] = []
    for i, line in enumerate(lines):
        x = BODY_X_MM + (indent_mm if i == 0 else 0)
        y = y_first_baseline + i * leading_mm
        parts.append(_emit_runs_line(line, x, y, attrs=attrs))
    return "".join(parts)


def render(page_id: int, data: dict) -> str:
    titulo = str(data.get("titulo", "")).strip()
    segments = data.get("segments") or []
    colophon = data.get("colophon") or []
    is_continuation = bool(data.get("is_continuation", False))

    parts = [r.svg_open(r.PALETTE["blanco"])]

    # — Title (first page only). First line's baseline sits at
    # row_bottom(1); wrapped lines stack downward into row 2.
    if titulo and not is_continuation:
        parts.append(r.text(
            "Indice-Titulo", titulo,
            x_mm=TITLE_X_MM, y_mm=TITLE_FIRST_BASELINE_Y_MM,
            max_width_mm=TITLE_MAX_W_MM,
        ))

    # — Body: each segment is a contiguous run of pre-wrapped lines.
    # First page body sits on row 3 (clearing the title above);
    # continuation pages start with their first baseline at the bottom
    # of row 1, leaving the same visual header band as the first page.
    # Segments are placed contiguously — no extra space between them,
    # since paragraph separation is conveyed entirely by the first-line
    # indent.
    if segments:
        y = (
            _CONT_PAGE_FIRST_BASELINE_Y_MM if is_continuation
            else _FIRST_PAGE_FIRST_BASELINE_Y_MM
        )
        for seg in segments:
            lines = seg.get("lines") or []
            indent = bool(seg.get("indent", False))
            parts.append(_emit_segment(lines, y, indent))
            y += len(lines) * _BODY_LEADING_MM

    # — Colophon (closing italic note, 10pt). Cap-top of the first line
    # sits on the top edge of row 7 — fixed slot regardless of where
    # the regular body ends. Stacks DOWNWARD with the 10pt leading.
    # No first-line sangría: italic + smaller size already mark it as
    # distinct from the regular paragraphs above.
    if colophon:
        parts.append(_emit_segment(
            colophon, _COLOPHON_FIRST_BASELINE_Y_MM, indent_first=False,
            leading_mm=_COLOPHON_LEADING_MM, attrs=_COLOPHON_LINE_ATTRS,
        ))

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)
