from inflacion.aplicacion.puertos import Almacen, FuenteDeSeries
from inflacion.dominio.series import Frecuencia, InfoSerie


def actualizar_catalogo(fuente: FuenteDeSeries, almacen: Almacen, frecuencias: list[Frecuencia]) -> list[InfoSerie]:
    """Baja el catálogo de las frecuencias pedidas y lo guarda ordenado por código.

    Sirve para elegir los códigos exactos de cada serie (el Banco Central los cambia cuando
    actualiza la base de un índice, como pasó con el IPC) en vez de copiarlos de memoria.
    """
    series = [s for f in frecuencias for s in fuente.catalogo(f)]
    series.sort(key=lambda s: (s.frecuencia.value, s.codigo))
    almacen.guardar_catalogo(series)
    return series
