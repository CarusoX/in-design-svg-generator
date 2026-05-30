"""Template registry.

A template is `render(page_id: int, data: dict) -> str` returning a full
<svg>...</svg> document. Templates referenced from catalog.yaml that aren't
registered here fall back to the placeholder so unimplemented pages still
render something visible during early development.
"""

from . import (
    placeholder,
    portada,
    epigrafe,
    nota_curatorial,
    indice,
    portadilla_sala,
    blank_red,
    blank_white,
    ficha_imagen,
    ficha_texto,
    bibliografia,
)

REGISTRY = {
    "placeholder": placeholder.render,
    "portada": portada.render,
    "epigrafe": epigrafe.render,
    "nota_curatorial": nota_curatorial.render,
    "indice": indice.render,
    "portadilla_sala": portadilla_sala.render,
    "blank_red": blank_red.render,
    "blank_white": blank_white.render,
    "ficha_imagen": ficha_imagen.render,
    "ficha_texto": ficha_texto.render,
    "bibliografia": bibliografia.render,
}


def get(name: str):
    return REGISTRY.get(name, placeholder.render)
