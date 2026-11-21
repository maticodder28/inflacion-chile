"""La competencia: para cada mes de encuesta, cada modelo pronostica con lo que se sabía ese día
y se compara con lo que dijeron los economistas y con lo que pasó de verdad.
"""

from dataclasses import dataclass

import pandas as pd

from inflacion.aplicacion.puertos import Almacen
from inflacion.dominio.disponibilidad import informacion_al
from inflacion.dominio.metricas import diebold_mariano, mae, rmse
from inflacion.dominio.modelos import Modelo

ECONOMISTAS = "Economistas (encuesta)"


@dataclass(frozen=True)
class Tarea:
    """Qué se pronostica y contra qué respuesta de la encuesta se compara."""

    nombre: str
    objetivo: str  # columna del panel que se quiere adivinar
    pasos: int  # meses entre el último dato conocido y el mes pronosticado
    columna_encuesta: str  # respuesta de los economistas en el mes de encuesta

    @property
    def desfase(self) -> int:
        """Meses entre el mes de encuesta y el mes pronosticado."""
        return self.pasos - 1


def backtest(
    panel: pd.DataFrame, tarea: Tarea, modelos: list[Modelo], rezagos: dict[str, int], desde: str, al_avanzar=None
) -> pd.DataFrame:
    """Una fila por mes de encuesta con el valor real, la encuesta y el pronóstico de cada modelo.

    Solo entran los meses cuyo resultado ya se conoce. Los modelos se vuelven a ajustar en cada mes
    (ventana que crece): es más lento, pero es exactamente lo que habría podido hacer alguien en ese momento.
    """
    real = panel[tarea.objetivo].shift(-tarea.desfase)
    meses = [
        m for m in panel.loc[desde:].index if pd.notna(real.get(m)) and pd.notna(panel.at[m, tarea.columna_encuesta])
    ]
    filas = []
    for i, origen in enumerate(meses):
        historia = informacion_al(panel, origen, rezagos)
        fila = {
            "encuesta": origen,
            "mes_pronosticado": origen + pd.DateOffset(months=tarea.desfase),
            "real": real[origen],
            ECONOMISTAS: panel.at[origen, tarea.columna_encuesta],
        }
        for m in modelos:
            fila[m.nombre] = m.pronosticar(historia, tarea.objetivo, tarea.pasos)
        filas.append(fila)
        if al_avanzar:
            al_avanzar(i + 1, len(meses))
    return pd.DataFrame(filas).set_index("encuesta")


PERIODOS = {
    "Todo": (None, None),
    "2010-2019 (inflación tranquila)": ("2010-01-01", "2019-12-01"),
    "2020-2023 (pandemia y shock)": ("2020-01-01", "2023-12-01"),
    "2024 en adelante": ("2024-01-01", None),
}


def resumen(resultados: pd.DataFrame, tarea: Tarea) -> pd.DataFrame:
    """Error de cada competidor por período, y si su diferencia con los economistas es estadísticamente real.

    Compara todos en los mismos meses: si un modelo no pudo pronosticar un mes, ese mes sale para todos.
    """
    competidores = [c for c in resultados.columns if c not in ("mes_pronosticado", "real")]
    completos = resultados.dropna(subset=competidores)
    filas = []
    for periodo, (ini, fin) in PERIODOS.items():
        tramo = completos.loc[ini:fin]
        if len(tramo) < 12:
            continue
        err_eco = tramo[ECONOMISTAS] - tramo["real"]
        for c in competidores:
            err = tramo[c] - tramo["real"]
            dm, p = (float("nan"), float("nan")) if c == ECONOMISTAS else diebold_mariano(err, err_eco, tarea.pasos)
            filas.append(
                {
                    "tarea": tarea.nombre,
                    "periodo": periodo,
                    "competidor": c,
                    "meses": len(tramo),
                    "mae": mae(err),
                    "rmse": rmse(err),
                    "mae_vs_economistas": mae(err) / mae(err_eco),
                    "dm": dm,
                    "p_valor": p,
                }
            )
    return pd.DataFrame(filas)


def competir(
    almacen: Almacen, tareas: list[tuple[Tarea, list[Modelo]]], rezagos: dict[str, int], desde: str, al_avanzar=None
) -> pd.DataFrame:
    """Corre todas las tareas con el panel guardado y deja los pronósticos y el resumen en el almacén."""
    panel = almacen.leer_panel()
    resumenes = []
    for tarea, modelos in tareas:
        resultados = backtest(
            panel, tarea, modelos, rezagos, desde, (lambda i, n, t=tarea: al_avanzar(t, i, n)) if al_avanzar else None
        )
        almacen.guardar_resultado(f"pronosticos_{tarea.objetivo}", resultados)
        resumenes.append(resumen(resultados, tarea))
    tabla = pd.concat(resumenes, ignore_index=True)
    almacen.guardar_resultado("resumen", tabla)
    return tabla


def pronostico_vigente(panel: pd.DataFrame, tarea: Tarea, modelos: list[Modelo], rezagos: dict[str, int]) -> dict:
    """La apuesta abierta: lo que dicen hoy los economistas y cada modelo para un mes que todavía no se conoce.

    Usa la última encuesta publicada; los modelos ven exactamente lo mismo que habrían visto ese día.
    """
    encuestas = panel[tarea.columna_encuesta].dropna()
    origen = encuestas.index[-1]
    historia = informacion_al(panel, origen, rezagos)
    return {
        "tarea": tarea.nombre,
        "encuesta": origen,
        "mes_pronosticado": origen + pd.DateOffset(months=tarea.desfase),
        "pronosticos": {ECONOMISTAS: float(encuestas.iloc[-1])}
        | {m.nombre: m.pronosticar(historia, tarea.objetivo, tarea.pasos) for m in modelos},
    }
