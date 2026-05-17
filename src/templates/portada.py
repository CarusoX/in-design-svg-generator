"""Portada — cover page on cream paper.

Layout mirrors reference page 1:
- Top label: "VOLUMEN N  ·  YEAR — YEAR" (gris_texto, tracked uppercase).
- Mid-page: tall red vertical rule + 3-line title (Lato Black) + italic
  serif subtitle.
- Bottom label: "X PIEZAS  ·  N SALAS" (same style as top label).
- No folio on the cover.

Expected `data` keys:
    volumen (str)    — e.g. "I"
    rango (str)      — e.g. "1764 — 2010"
    titulo (str)     — title with explicit "\\n" for editorial line breaks
    subtitulo (str)  — italic serif subtitle (auto-wraps)
    piezas (str|int) — e.g. "57 piezas" (uppercased by style)
    salas (str|int)  — e.g. "7 salas"
"""

from __future__ import annotations

from .. import render as r


# Title block geometry (measured against reference page 1).
TITLE_X_MM = 22          # right of the red rule + small gap
TITLE_FIRST_Y_MM = 105   # first-line baseline
RULE_X_MM = 14
RULE_Y_MM = 92
RULE_H_MM = 60           # per spec for cover rule


def render(page_id: int, data: dict) -> str:
    parts = [r.svg_open(r.PALETTE["papel_crema"])]

    # — Top label: "VOLUMEN I  ·  1764 — 2010"
    volumen = str(data.get("volumen", "")).strip()
    rango = str(data.get("rango", "")).strip()
    top_segments = [s for s in (f"Volumen {volumen}" if volumen else "", rango) if s]
    if top_segments:
        parts.append(r.text(
            "01-Portada-Label",
            "  ·  ".join(top_segments),
            x_mm=r.MARGIN_MM,
            y_mm=22,
        ))

    # — Red vertical rule (decorative, runs alongside the title block)
    parts.append(r.red_rule_vertical(RULE_X_MM, RULE_Y_MM, RULE_H_MM))

    # — Title (manual line breaks via "\n" in YAML)
    titulo = str(data.get("titulo", "")).strip()
    if titulo:
        parts.append(r.text(
            "02-Portada-Titulo",
            titulo,
            x_mm=TITLE_X_MM,
            y_mm=TITLE_FIRST_Y_MM,
            max_width_mm=r.CONTENT_W_MM - (TITLE_X_MM - r.MARGIN_MM),
        ))

    # — Subtitle (italic serif, gris_texto, auto-wraps)
    subtitulo = str(data.get("subtitulo", "")).strip()
    if subtitulo:
        parts.append(r.text(
            "03-Portada-Subtitulo",
            subtitulo,
            x_mm=TITLE_X_MM,
            y_mm=160,
            max_width_mm=r.CONTENT_W_MM - (TITLE_X_MM - r.MARGIN_MM),
        ))

    # — Bottom label: "57 PIEZAS  ·  7 SALAS"
    piezas = str(data.get("piezas", "")).strip()
    salas = str(data.get("salas", "")).strip()
    bottom_segments = [s for s in (piezas, salas) if s]
    if bottom_segments:
        parts.append(r.text(
            "01-Portada-Label",
            "  ·  ".join(bottom_segments),
            x_mm=r.MARGIN_MM,
            y_mm=r.TRIM_H_MM - 14,
        ))

    parts.append(r.svg_close())
    return "".join(parts)
