"""Lo que los casos de uso necesitan del exterior, escrito como interfaces.

La implementación real (API del Banco Central, archivos CSV) está en infraestructura/.
Los tests usan implementaciones falsas en memoria.
"""

from typing import Protocol

from inflacion.dominio.series import Frecuencia, InfoSerie


class FuenteDeSeries(Protocol):
    def catalogo(self, frecuencia: Frecuencia) -> list[InfoSerie]: ...


class Almacen(Protocol):
    def guardar_catalogo(self, series: list[InfoSerie]) -> None: ...
