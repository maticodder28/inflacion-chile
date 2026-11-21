"""Lee config/series.toml y lo convierte en definiciones del dominio."""

import tomllib
from pathlib import Path

from inflacion.dominio.series import DefSerie


def leer_series(archivo: Path) -> list[DefSerie]:
    datos = tomllib.loads(archivo.read_text(encoding="utf-8"))
    return [
        DefSerie(
            nombre=s["nombre"],
            descripcion=s["descripcion"],
            codigos=tuple(s["codigos"]),
            agregacion=s.get("agregacion"),
        )
        for s in datos["serie"]
    ]
