"""Design-system source of truth: color palette and paragraph styles.

PALETTE and TEXT_STYLES are the only place templates should look for
colors / typography. No template should inline hex literals or font names.
"""

from dataclasses import dataclass


PALETTE: dict[str, str] = {
    "rojo_tinta":   "#A92A20",   # matches tests/ground-truth/Section1.svg
    "papel_crema":  "#F5F2EB",
    "negro_tinta":  "#1A1A1A",
    "gris_texto":   "#555555",
    "gris_claro":   "#999999",
    "frame_fill":   "#EBE7DD",
    "frame_stroke": "#C8C1B0",
}


@dataclass(frozen=True)
class TextStyle:
    font_family: str
    font_weight: int = 400           # 400 regular, 700 bold, 900 black
    font_style: str = "normal"       # "normal" | "italic"
    size_pt: float = 10.0
    leading_pt: float | None = None  # absolute line height; None = auto
    tracking_per1000: int = 0        # InDesign tracking units (1/1000 em)
    color: str = "negro_tinta"       # PALETTE key
    uppercase: bool = False
    align: str = "start"             # "start" | "middle" | "end"
    space_before_mm: float = 0.0
    space_after_mm: float = 0.0
    first_line_indent_mm: float = 0.0
    hanging_indent_mm: float = 0.0
    justified: bool = False


# IDs match the InDesign Paragraph Style names (see CLAUDE.md). Numeric
# prefix is preserved so the operator's Paragraph Styles panel sorts the
# same as this registry.
TEXT_STYLES: dict[str, TextStyle] = {
    # — Portada (cover) —
    "01-Portada-Label": TextStyle(
        # Reference uses gris_texto, not rojo_tinta (the red rule on the
        # cover already carries the brand color; labels stay neutral).
        font_family="Lato", font_weight=900,
        size_pt=8, leading_pt=11,
        tracking_per1000=200,
        color="gris_texto", uppercase=True,
    ),
    "02-Portada-Titulo": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=42, leading_pt=40,
        tracking_per1000=-20,
        color="negro_tinta",
    ),
    "03-Portada-Subtitulo": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=12, leading_pt=16,
        color="gris_texto",
        space_before_mm=10,
    ),

    # — Epígrafe (red-bg quote spread) —
    "04-Epigrafe-Label": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=7, leading_pt=9,
        tracking_per1000=200,
        color="papel_crema", uppercase=True,
        align="middle",
    ),
    "05-Epigrafe-Cita": TextStyle(
        # Regular weight 500 (not italic). Centered on the page.
        font_family="EB Garamond", font_weight=500,
        size_pt=22, leading_pt=26,
        color="papel_crema",
        align="middle",
    ),
    "06-Epigrafe-Fuente": TextStyle(
        # Reference centers the source line, not right-aligns (spec was wrong).
        font_family="EB Garamond", font_style="italic",
        size_pt=10, leading_pt=14,
        color="papel_crema",
        align="middle",
    ),

    # — Curatorial note / section headers —
    "07-Seccion-Label": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=7, leading_pt=9,
        tracking_per1000=200,
        color="rojo_tinta", uppercase=True,
    ),
    "08-Seccion-Titulo": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=22, leading_pt=23,
        tracking_per1000=-10,
        color="negro_tinta",
        space_after_mm=12,
    ),
    "09-Body-Garamond": TextStyle(
        font_family="EB Garamond",
        size_pt=10, leading_pt=15.5,
        color="negro_tinta",
        justified=True,
        first_line_indent_mm=5,
    ),

    # — Índice —
    # Title for the índice page — identical to 08-Seccion-Titulo (Lato
    # Black 22pt) but in rojo_tinta instead of negro_tinta. Used only
    # by the índice template.
    "Indice-Titulo": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=22, leading_pt=23,
        tracking_per1000=-10,
        color="rojo_tinta",
        space_after_mm=12,
    ),
    "10-Indice-Romano": TextStyle(
        font_family="EB Garamond",
        size_pt=16,
        color="rojo_tinta",
    ),
    "11-Indice-Sala": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=11, leading_pt=14,
        color="negro_tinta",
    ),
    "12-Indice-Periodo": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=9,
        color="gris_texto",
        align="end",
    ),

    # — Portadilla de sala (red-bg section title page) —
    "13-Portadilla-Romano": TextStyle(
        # Size 156.71pt to match tests/ground-truth/Section1.svg.
        font_family="EB Garamond",
        size_pt=156.71, leading_pt=155,
        color="papel_crema",
    ),
    "14-Portadilla-Nombre": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=20, leading_pt=22,
        tracking_per1000=-10,
        color="papel_crema",
        space_before_mm=6,
        justified=True,
    ),
    "15-Portadilla-Periodo": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=8, leading_pt=10,
        tracking_per1000=200,
        color="papel_crema", uppercase=True,
    ),
    "16-Portadilla-CitaCurato": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=13, leading_pt=18,
        color="papel_crema",
        justified=True,
    ),

    # — Fichas (artwork cards, both pages of the spread) —
    "17-Ficha-Cabecera-ID": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=6.5, leading_pt=9,
        tracking_per1000=150,
        color="rojo_tinta", uppercase=True,
    ),
    "18-Ficha-Cabecera-Sub": TextStyle(
        font_family="Lato", font_weight=900,
        size_pt=6.5, leading_pt=9,
        tracking_per1000=150,
        color="gris_texto", uppercase=True,
        align="end",
    ),
    "19-Ficha-Tipo": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=8.5, leading_pt=11,
        color="rojo_tinta",
    ),
    "20-Ficha-Titulo-Pieza": TextStyle(
        font_family="Lato", font_weight=700,
        size_pt=18, leading_pt=22.5,
        tracking_per1000=-15,
        color="negro_tinta",
    ),
    "21-Ficha-Subtitulo-Autor": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=9, leading_pt=12,
        color="negro_tinta",
    ),
    "22-Ficha-Subtitulo-Datos": TextStyle(
        font_family="EB Garamond",
        size_pt=9, leading_pt=12,
        color="gris_texto",
    ),
    "23-Ficha-Epigrafe-Imagen": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=7.5, leading_pt=10,
        color="gris_texto",
    ),
    "24-Ficha-Descripcion": TextStyle(
        # Left-aligned (ragged right). Hyphenation in wrap_lines keeps
        # the rag tight; justification adds little once hyphens are in.
        font_family="EB Garamond",
        size_pt=10, leading_pt=15,
        color="negro_tinta",
    ),
    "25-Ficha-CitaTextual": TextStyle(
        # Reference uses EB Garamond Italic, not Caveat — see CLAUDE.md note.
        font_family="EB Garamond", font_style="italic",
        size_pt=14, leading_pt=18,
        color="rojo_tinta",
    ),
    "26-Ficha-Fuente": TextStyle(
        font_family="Lato",
        size_pt=6.5, leading_pt=10,
        tracking_per1000=50,
        color="gris_texto",
    ),

    # — Bibliografía —
    "27-Biblio-Referencia": TextStyle(
        font_family="EB Garamond",
        size_pt=9, leading_pt=13.5,
        color="negro_tinta",
        justified=True,
        hanging_indent_mm=5,
    ),

    # — Auxiliary: ficha metadata VALUE (used in ficha_texto's stack
    # under each AUTOR / ESTADO / FECHA / ORIGEN label). Plain regular
    # Garamond, black, not italic — wraps with hyphenation. —
    "Ficha-Meta-Value": TextStyle(
        font_family="EB Garamond",
        size_pt=9, leading_pt=12,
        color="negro_tinta",
    ),

    # — Top-left metadata stack on ficha_texto (Fecha / Origen / Autor /
    # Estado). Small italic gray, no labels — values stack tightly. —
    "Ficha-Meta-Top": TextStyle(
        font_family="EB Garamond", font_style="italic",
        size_pt=8.5, leading_pt=11,
        color="gris_texto",
    ),

    # — Auxiliary: page numbers (folios). Not in the original spec — added
    # so templates can place the page number without inlining font/size. —
    "Folio-Light": TextStyle(
        font_family="Lato", font_weight=400,
        size_pt=8,
        color="papel_crema",
    ),
    "Folio-Dark": TextStyle(
        font_family="Lato", font_weight=400,
        size_pt=8,
        color="gris_texto",
    ),
}
