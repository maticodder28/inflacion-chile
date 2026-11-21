"""Lo que los casos de uso necesitan del exterior, escrito como interfaces.

La implementación real (API del Banco Central, archivos CSV) está en infraestructura/.
Los tests usan implementaciones falsas en memoria.
"""

from datetime import date
from typing import Protocol

import pandas as pd

from inflacion.dominio.series import Frecuencia, InfoSerie


class FuenteDeSeries(Protocol):
    def catalogo(self, frecuencia: Frecuencia) -> list[InfoSerie]: ...

    def observaciones(self, codigo: str, desde: date, hasta: date) -> pd.Series:
        """Valores de la serie indexados por fecha, sin los datos faltantes."""
        ...


class Almacen(Protocol):
    def guardar_catalogo(self, series: list[InfoSerie]) -> None: ...

    def guardar_panel(self, panel: pd.DataFrame) -> None: ...

    def leer_panel(self) -> pd.DataFrame: ...

    def guardar_resultado(self, nombre: str, tabla: pd.DataFrame) -> None: ...
