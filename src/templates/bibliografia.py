"""Bibliografía — paginated references list on cream paper.

Chrome mirrors the índice page:
- "Bibliografía" title in Lato Black 22pt red (`Indice-Titulo`),
  baseline anchored to the BOTTOM of cell (row 1, col 1). Renders only
  on the first page; continuation pages skip it.
- Each reference uses `27-Biblio-Referencia` (EB Garamond 9/13.5pt)
  with a 5mm HANGING indent — author surname sticks out at LEFT_X and
  the wrapped continuation lines tuck under the title text. A half-
  leading gap separates consecutive references.
- Folio in the outer margin.

URL handling: long URLs in references can't break with normal word-
wrap (no whitespace inside them, no syllables for pyphen to find), so
`_tokenize_for_biblio` splits each URL at every "/" — each chunk
becomes its own wrap token marked `sticky=True` so the wrap doesn't
insert visible spaces between chunks. The line still breaks at any
chunk boundary when it overflows, but the rendered URL reads as one
continuous string.

`paginate()` is the entry point — it splits the referencias list
across pages so each page fills line-by-line. Refs are atomic (never
split across pages); when one doesn't fit, the page flushes and the
ref starts at the top of the next page.

Per-page `data` shape (produced by `paginate`, consumed by `render`):
    titulo (str, optional)           — first page only
    is_continuation (bool, optional) — every page after the first
    refs (list[list[str]])           — each item is one reference,
        pre-wrapped to a list of line strings (line[0] sits at LEFT_X,
        line[1..] are indented by HANGING_INDENT_MM).
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

from .. import render as r
from ..styles import TEXT_STYLES
from . import _ficha_common as ch


_GARAMOND_CAP_RATIO = 0.685

# Title (same anchor as the índice / nota_curatorial pages).
TITLE_X_MM = ch.LEFT_X_MM
TITLE_BASELINE_Y_MM = ch.row_bottom(1)

# References — full reticle width.
REF_X_MM = ch.LEFT_X_MM
REF_MAX_W_MM = ch.RIGHT_X_MM - ch.LEFT_X_MM
_REF_STYLE = TEXT_STYLES["27-Biblio-Referencia"]
_REF_STYLE_ID = "27-Biblio-Referencia"
_REF_CAP_H_MM = _GARAMOND_CAP_RATIO * _REF_STYLE.size_pt * r.MM_PER_PT
_REF_LEADING_MM = (
    (_REF_STYLE.leading_pt or _REF_STYLE.size_pt * 1.2) * r.MM_PER_PT
)
_REF_DESC_MM = 0.21 * _REF_STYLE.size_pt * r.MM_PER_PT

HANGING_INDENT_MM = 5.0
# Half-leading visible gap between consecutive refs.
ENTRY_GAP_MM = _REF_LEADING_MM / 2

# Page geometry — refs start on row 3 of the first page (clearing the
# title above) and on row 1 of continuation pages (anchored to the
# bottom of row 1, mirroring how nota_curatorial starts its body).
_PAGE_BOTTOM_Y_MM = ch.row_bottom(9)
_FIRST_PAGE_FIRST_BASELINE_Y_MM = ch.row_top(3) + _REF_CAP_H_MM
_CONT_PAGE_FIRST_BASELINE_Y_MM = ch.row_bottom(1)


def _line_capacity(first_baseline_y_mm: float) -> int:
    budget = _PAGE_BOTTOM_Y_MM - first_baseline_y_mm - _REF_DESC_MM
    return max(1, 1 + int(budget // _REF_LEADING_MM))


FIRST_PAGE_LINE_CAPACITY = _line_capacity(_FIRST_PAGE_FIRST_BASELINE_Y_MM)
CONT_PAGE_LINE_CAPACITY = _line_capacity(_CONT_PAGE_FIRST_BASELINE_Y_MM)

# How much of a line one ENTRY_GAP_MM eats — used during pagination so
# the gap counts toward the page's vertical budget.
_GAP_LINE_EQUIV = ENTRY_GAP_MM / _REF_LEADING_MM


# ── Tokenization with URL-aware splitting ────────────────────────────

_URL_PATTERN = re.compile(r"^https?://")
# Break chars whose presence creates a wrap opportunity inside a URL.
# `_AFTER` chars stay attached to the PRECEDING chunk (so the line
# ends with "…/" or "….") — these read naturally at a line end.
# `_BEFORE` chars (just "-") stay attached to the FOLLOWING chunk,
# because a trailing "-" at end of line reads as soft hyphenation,
# which is misleading when it's actually a literal dash inside a URL.
_URL_BREAK_AFTER_RE = re.compile(r"([/_.?&=])")
_URL_BREAK_BEFORE_RE = re.compile(r"(-)")
_NUL = "\x00"


def _split_url(url: str) -> list[str]:
    s = _URL_BREAK_AFTER_RE.sub(r"\1" + _NUL, url)
    s = _URL_BREAK_BEFORE_RE.sub(_NUL + r"\1", s)
    return [c for c in s.split(_NUL) if c]


def _tokenize_for_biblio(text: str) -> list[tuple[str, bool, bool]]:
    """Split text into (token, sticky, is_url) triples. Plain words are
    non-sticky, non-URL (inter-word space when joined). URLs are split
    at every break opportunity (see `_split_url`); chunks after the
    first are marked sticky=True so the URL renders as one contiguous
    string but can break at any chunk boundary. Every URL chunk is
    marked is_url=True so the renderer can wrap it in a
    `text-decoration="underline"` tspan."""
    out: list[tuple[str, bool, bool]] = []
    for word in text.split():
        if _URL_PATTERN.match(word):
            for i, chunk in enumerate(_split_url(word)):
                out.append((chunk, i > 0, True))
        else:
            out.append((word, False, False))
    return out


# ── Wrap (hanging-indent, URL-sticky aware) ──────────────────────────

def _wrap_ref(
    tokens: list[tuple[str, bool, bool]], max_w_mm: float,
    hanging_indent_mm: float,
) -> list[list[tuple[str, bool, bool]]]:
    """Wrap tokens. Line 0 uses full `max_w_mm`; later lines use
    `max_w_mm - hanging_indent_mm`. Sticky tokens (URL chunks past the
    first) contribute their bare width — no inter-token space — so
    URLs render contiguously and may break at any chunk boundary.
    is_url is preserved unchanged for the renderer."""
    space_mm = r._measure_word_mm(" ", _REF_STYLE)
    rest_max = max(1.0, max_w_mm - hanging_indent_mm)

    lines: list[list[tuple[str, bool, bool]]] = []
    current: list[tuple[str, bool, bool]] = []
    current_w_mm = 0.0
    current_max_mm = max_w_mm
    for token, sticky, is_url in tokens:
        token_w_mm = r._measure_word_mm(token, _REF_STYLE)
        if not current:
            added_w_mm = token_w_mm
            token_sticky = False
        elif sticky:
            added_w_mm = token_w_mm
            token_sticky = True
        else:
            added_w_mm = space_mm + token_w_mm
            token_sticky = False
        if current and current_w_mm + added_w_mm > current_max_mm:
            lines.append(current)
            current = [(token, False, is_url)]
            current_w_mm = token_w_mm
            current_max_mm = rest_max
        else:
            current.append((token, token_sticky, is_url))
            current_w_mm += added_w_mm
    if current:
        lines.append(current)
    return lines


def _line_to_runs(
    line_tokens: list[tuple[str, bool, bool]],
) -> list[tuple[str, bool]]:
    """Collapse tokens into renderable runs of `(text, is_url)`. Inter-
    token spaces (where sticky=False) are emitted as non-URL characters
    so the underline doesn't visibly extend into the space before a URL.
    Adjacent same-`is_url` chars merge into one run, which keeps the
    SVG compact (typically 1–3 tspans per line)."""
    if not line_tokens:
        return []
    pieces: list[tuple[str, bool]] = []  # (char, is_url)
    for i, (token, sticky, is_url) in enumerate(line_tokens):
        if i > 0 and not sticky:
            pieces.append((" ", False))
        for ch_ in token:
            pieces.append((ch_, is_url))
    runs: list[tuple[str, bool]] = []
    cur_text, cur_url = pieces[0]
    for c, u in pieces[1:]:
        if u == cur_url:
            cur_text += c
        else:
            runs.append((cur_text, cur_url))
            cur_text, cur_url = c, u
    runs.append((cur_text, cur_url))
    return runs


# ── Rendering helpers ────────────────────────────────────────────────

def _ref_line_attrs() -> str:
    style = _REF_STYLE
    fill = r.PALETTE[style.color]
    size_mm = style.size_pt * r.MM_PER_PT
    return (
        f'font-family="{r.font_family_css(style.font_family, style.font_weight)}" '
        f'font-size="{size_mm:.4f}" font-weight="{style.font_weight}" '
        f'fill="{fill}" text-anchor="{style.align}"'
    )


_REF_LINE_ATTRS = _ref_line_attrs()


def _emit_biblio_line(
    runs: list[tuple[str, bool]], x_mm: float, y_mm: float,
) -> str:
    """Emit one wrapped line as a `<text>` with one `<tspan>` per run.
    URL runs get the SVG presentation attribute `text-decoration="underline"`
    so the renderer applies the font's own underline metrics (thickness +
    position drawn from the font tables) — InDesign honours this on
    import too. Tspans after the first omit `x` so they flow
    horizontally from where the previous one ended."""
    if not runs:
        return ""
    parts = [
        f'<text xml:space="preserve" x="{x_mm}" y="{y_mm}" '
        f'{_REF_LINE_ATTRS}>'
    ]
    for text, is_url in runs:
        if is_url:
            parts.append(
                f'<tspan text-decoration="underline">{escape(text)}</tspan>'
            )
        else:
            parts.append(f'<tspan>{escape(text)}</tspan>')
    parts.append('</text>')
    return "".join(parts)


# ── Pagination ───────────────────────────────────────────────────────

def paginate(data: dict) -> list[dict]:
    """Pack references atomically into pages. Each page fills line-by-
    line; when a ref doesn't fit, the page flushes and the ref starts
    at the top of the next page."""
    titulo = str(data.get("titulo", "Bibliografía")).strip()
    referencias = [
        str(s).strip() for s in (data.get("referencias") or []) if str(s).strip()
    ]

    # Pre-wrap each ref. Each ref becomes a list of lines; each line is
    # a list of `(text, is_url)` runs ready for `_emit_biblio_line`.
    ref_lines_per: list[list[list[tuple[str, bool]]]] = []
    for ref in referencias:
        tokens = _tokenize_for_biblio(ref)
        wrapped = _wrap_ref(tokens, REF_MAX_W_MM, HANGING_INDENT_MM)
        ref_lines_per.append([_line_to_runs(line) for line in wrapped])

    pages: list[dict] = []
    cur_refs: list[list[list[tuple[str, bool]]]] = []
    cur_lines = 0.0   # accumulated line-equivalent units

    def cap() -> int:
        return CONT_PAGE_LINE_CAPACITY if pages else FIRST_PAGE_LINE_CAPACITY

    def flush() -> None:
        nonlocal cur_refs, cur_lines
        if not cur_refs:
            return
        page: dict = {"refs": cur_refs}
        if pages:
            page["is_continuation"] = True
        elif titulo:
            page["titulo"] = titulo
        pages.append(page)
        cur_refs = []
        cur_lines = 0.0

    for ref_lines in ref_lines_per:
        n = len(ref_lines)
        cost = n + (_GAP_LINE_EQUIV if cur_refs else 0.0)
        if cur_refs and cur_lines + cost > cap():
            flush()
            cost = n
        cur_refs.append(ref_lines)
        cur_lines += cost

    flush()

    if not pages and titulo:
        # No refs at all — emit a single page with just the title so
        # the section still anchors a page slot in the catalog.
        pages.append({"titulo": titulo, "refs": []})

    return pages


# ── Rendering ────────────────────────────────────────────────────────

def render(page_id: int, data: dict) -> str:
    titulo = str(data.get("titulo", "")).strip()
    refs = data.get("refs") or []
    is_continuation = bool(data.get("is_continuation", False))

    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    if titulo and not is_continuation:
        parts.append(r.text(
            "Indice-Titulo", titulo,
            x_mm=TITLE_X_MM, y_mm=TITLE_BASELINE_Y_MM,
        ))

    if refs:
        y = (
            _CONT_PAGE_FIRST_BASELINE_Y_MM if is_continuation
            else _FIRST_PAGE_FIRST_BASELINE_Y_MM
        )
        for ref_lines in refs:
            for i, line_runs in enumerate(ref_lines):
                x = REF_X_MM + (HANGING_INDENT_MM if i > 0 else 0)
                parts.append(_emit_biblio_line(line_runs, x, y))
                y += _REF_LEADING_MM
            y += ENTRY_GAP_MM

    parts.append(r.folio(page_id))
    parts.append(r.svg_close())
    return "".join(parts)
