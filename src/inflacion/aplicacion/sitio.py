"""Arma los datos del dashboard público: todo lo que la página necesita, en un solo JSON."""

import math

import pandas as pd

from inflacion.aplicacion.competencia import ECONOMISTAS, Tarea, pronostico_vigente
from inflacion.dominio import analisis
from inflacion.dominio.modelos import Modelo


def _num(v) -> float | None:
    """NaN no existe en JSON: lo paso a null."""
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), 3)


def _mes(fecha) -> str:
    return pd.Timestamp(fecha).strftime("%Y-%m")


def datos_sitio(
    panel: pd.DataFrame,
    resumen: pd.DataFrame,
    pronosticos_mes: pd.DataFrame,
    tareas: list[tuple[Tarea, list[Modelo]]],
    rezagos: dict[str, int],
) -> dict:
    ipc = panel["ipc_12m"].dropna()
    # Lo esperado un año antes para cada mes, incluidos los meses que todavía no pasan.
    esperado = panel["eee_12m_en_11"].dropna()
    esperado.index = esperado.index + pd.DateOffset(months=11)
    meses = ipc.loc["2010":].index.union(esperado.loc["2010":].index)
    serie_12m = [{"mes": _mes(m), "real": _num(ipc.get(m)), "esperado": _num(esperado.get(m))} for m in meses]

    ultimos = pronosticos_mes.tail(36)
    mensual = [
        {"mes": _mes(m), "real": _num(f["real"]), "economistas": _num(f[ECONOMISTAS]), "sarima": _num(f["SARIMA"])}
        for m, f in ultimos.iterrows()
    ]
    vigentes = []
    for tarea, modelos in tareas:
        v = pronostico_vigente(panel, tarea, modelos, rezagos)
        vigentes.append(
            {
                "tarea": v["tarea"],
                "encuesta": _mes(v["encuesta"]),
                "mes_pronosticado": _mes(v["mes_pronosticado"]),
                "pronosticos": [{"competidor": c, "valor": _num(x)} for c, x in v["pronosticos"].items()],
            }
        )
    ep = analisis.episodio_alto(ipc)
    return {
        "actualizado": _mes(ipc.index[-1]),
        "economistas": ECONOMISTAS,
        "ultimo_ipc_12m": _num(ipc.iloc[-1]),
        "tpm": _num(panel["tpm"].dropna().iloc[-1]),
        "episodio": {
            "desde": _mes(ep["desde"]),
            "hasta": _mes(ep["hasta"]),
            "meses": ep["meses"],
            "peak": ep["peak"],
            "mes_peak": _mes(ep["mes_peak"]),
        }
        if ep
        else None,
        "resumen": [
            {
                k: (_num(f[k]) if k in ("mae", "rmse", "p_valor", "mae_vs_economistas") else f[k])
                for k in ("tarea", "periodo", "competidor", "meses", "mae", "rmse", "mae_vs_economistas", "p_valor")
            }
            for _, f in resumen.iterrows()
        ],
        "serie_12m": serie_12m,
        "mensual": mensual,
        "vigentes": vigentes,
    }
