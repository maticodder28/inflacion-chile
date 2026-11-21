"""La regla de dependencias de Clean Architecture, como test: si alguien la rompe, el CI falla."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "inflacion"

# Lo que NO puede importar cada capa.
PROHIBIDO = {
    "dominio": ("inflacion.aplicacion", "inflacion.infraestructura", "inflacion.presentacion", "requests", "tomllib"),
    "aplicacion": ("inflacion.infraestructura", "inflacion.presentacion", "requests"),
    "infraestructura": ("inflacion.presentacion",),
}


def importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            nombres.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            nombres.add(n.module)
    return nombres


@pytest.mark.parametrize("capa", PROHIBIDO)
def test_cada_capa_depende_solo_hacia_adentro(capa):
    malos = [
        f"{archivo.relative_to(SRC)} importa {m}"
        for archivo in (SRC / capa).rglob("*.py")
        for m in importados(archivo)
        if m.startswith(PROHIBIDO[capa])
    ]
    assert not malos, "\n".join(malos)
