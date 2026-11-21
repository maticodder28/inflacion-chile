"""Lo que es una serie para este proyecto, sin importar de dónde venga."""

from dataclasses import dataclass
from enum import StrEnum


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
