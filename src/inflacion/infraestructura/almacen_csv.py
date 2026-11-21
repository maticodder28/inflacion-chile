"""Guarda los datos como CSV dentro del repo, así quedan versionados y cualquiera puede revisarlos."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from inflacion.dominio.series import InfoSerie


class AlmacenCSV:
    def __init__(self, carpeta: Path):
        self.carpeta = carpeta

    def guardar_catalogo(self, series: list[InfoSerie]) -> None:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        filas = [{**asdict(s), "frecuencia": s.frecuencia.value} for s in series]
        pd.DataFrame(filas).to_csv(self.carpeta / "catalogo.csv", index=False)

    def guardar_panel(self, panel: pd.DataFrame) -> None:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        panel.to_csv(self.carpeta / "panel_mensual.csv", float_format="%.6g", date_format="%Y-%m-%d")
