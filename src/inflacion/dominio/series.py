"""Lo que es una serie para este proyecto, sin importar de dónde venga.

Uso pandas en el dominio a propósito: para series de tiempo es el lenguaje común, no un detalle de
infraestructura. Lo que el dominio no puede tocar es la red ni los archivos.
"""

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class Frecuencia(StrEnum):
    DIARIA = "DAILY"
    MENSUAL = "MONTHLY"
    TRIMESTRAL = "QUARTERLY"
    ANUAL = "ANNUAL"


@dataclass(frozen=True)
class InfoSerie:
    """Una fila del catálogo del Banco Central: código, título y qué fechas cubre."""

    codigo: str
    titulo: str
    frecuencia: Frecuencia
    primera: str | None
    ultima: str | None


@dataclass(frozen=True)
class DefSerie:
    """Una serie que usa el proyecto: nombre corto, de dónde sale y cómo se lleva a mensual."""

    nombre: str
    descripcion: str
    codigos: tuple[str, ...]
    agregacion: str | None = None  # "promedio" | "ultimo" para series diarias
    rezago: int = 1  # meses que tarda en publicarse, contados desde el mes de la encuesta

    def __post_init__(self):
        if not self.codigos:
            raise ValueError(f"La serie {self.nombre} no tiene códigos.")
        if self.agregacion not in (None, "promedio", "ultimo"):
            raise ValueError(f"Agregación desconocida en {self.nombre}: {self.agregacion}")


def empalmar(partes: list[pd.Series]) -> pd.Series:
    """Une los tramos de una serie que cambió de base. Donde se traslapan, manda el tramo más nuevo."""
    partes = [p.dropna() for p in partes if p is not None and not p.dropna().empty]
    if not partes:
        return pd.Series(dtype=float)
    unida = partes[0]
    for p in partes[1:]:
        unida = p.combine_first(unida)
    return unida.sort_index()


def a_mensual(serie: pd.Series, agregacion: str | None) -> pd.Series:
    """Deja la serie con un dato por mes, fechado el primer día del mes (como las mensuales del Banco Central)."""
    serie = serie.dropna().sort_index()
    if serie.empty:
        return serie
    mes = serie.index.to_period("M")
    if agregacion is None:
        # Ya es mensual: si por algún motivo hay dos datos en un mes, me quedo con el último.
        mensual = serie.groupby(mes).last()
    elif agregacion == "promedio":
        mensual = serie.groupby(mes).mean()
    else:
        mensual = serie.groupby(mes).last()
    mensual.index = mensual.index.to_timestamp()
    return mensual
