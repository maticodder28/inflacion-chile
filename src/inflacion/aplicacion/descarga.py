from datetime import date

import pandas as pd

from inflacion.aplicacion.puertos import Almacen, FuenteDeSeries
from inflacion.dominio.series import DefSerie, a_mensual, empalmar


def descargar_panel(
    fuente: FuenteDeSeries, almacen: Almacen, defs: list[DefSerie], desde: date, hasta: date
) -> pd.DataFrame:
    """Baja cada serie, empalma sus tramos, la lleva a mensual y arma el panel: una fila por mes y una columna
    por serie."""
    columnas = {}
    for d in defs:
        partes = [fuente.observaciones(c, desde, hasta) for c in d.codigos]
        columnas[d.nombre] = a_mensual(empalmar(partes), d.agregacion)
    panel = pd.DataFrame(columnas).sort_index()
    panel.index.name = "mes"
    almacen.guardar_panel(panel)
    return panel
