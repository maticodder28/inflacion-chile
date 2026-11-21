"""Cálculos del análisis exploratorio. Funciones puras sobre el panel mensual, para que los números del
informe y de los gráficos salgan de un solo lugar y tengan tests.
"""

import numpy as np
import pandas as pd

META = 3.0
RANGO_META = (2.0, 4.0)  # el Banco Central tolera entre 2% y 4%


def acumulada_12m(variacion_mensual: pd.Series) -> pd.Series:
    """Variación en 12 meses a partir de las variaciones mensuales (%): se componen, no se suman."""
    factor = (1 + variacion_mensual / 100).rolling(12).apply(np.prod, raw=True)
    return 100 * (factor - 1)


def var_12m(serie: pd.Series) -> pd.Series:
    """Variación porcentual contra el mismo mes del año anterior."""
    return 100 * (serie / serie.shift(12) - 1)


def episodio_alto(ipc_12m: pd.Series, umbral: float = RANGO_META[1]) -> dict:
    """El tramo más largo de meses seguidos con la inflación sobre el techo del rango meta, y su peak."""
    sobre = ipc_12m > umbral
    grupos = (sobre != sobre.shift()).cumsum()[sobre]
    if grupos.empty:
        return {}
    mas_largo = grupos.value_counts().idxmax()
    tramo = ipc_12m[grupos[grupos == mas_largo].index]
    return {
        "desde": tramo.index[0],
        "hasta": tramo.index[-1],
        "meses": len(tramo),
        "peak": float(tramo.max()),
        "mes_peak": tramo.idxmax(),
    }


def estacionalidad(ipc_mensual: pd.Series, desde: str, hasta: str) -> pd.Series:
    """Inflación mensual promedio por mes calendario (1 = enero). Uso años normales para que un shock no la tuerza."""
    tramo = ipc_mensual.loc[desde:hasta]
    return tramo.groupby(tramo.index.month).mean()


def traspaso_dolar(panel: pd.DataFrame, max_rezago: int = 18) -> pd.DataFrame:
    """Correlación entre el alza del dólar en 12 meses y la inflación 12 meses k meses después.

    Responde cuánto tarda el dólar en llegar a los precios. Es una correlación, no un efecto causal:
    en 2021 subieron el dólar y la inflación a la vez por varias razones.
    """
    dolar = var_12m(panel["dolar"])
    ipc = panel["ipc_12m"]
    filas = [{"rezago": k, "correlacion": ipc.corr(dolar.shift(k))} for k in range(max_rezago + 1)]
    return pd.DataFrame(filas)


def coeficiente_traspaso(panel: pd.DataFrame, rezago: int) -> float:
    """Pendiente de la regresión del IPC 12m sobre el alza del dólar con ese rezago: pp de inflación por cada
    10% que sube el dólar."""
    datos = pd.DataFrame({"ipc": panel["ipc_12m"], "dolar": var_12m(panel["dolar"]).shift(rezago)}).dropna()
    pendiente = np.polyfit(datos["dolar"], datos["ipc"], 1)[0]
    return float(pendiente * 10)


def tasa_real_esperada(panel: pd.DataFrame) -> pd.Series:
    """TPM menos la inflación que esperan los economistas a un año: si es positiva, la política está apretando."""
    return panel["tpm"] - panel["eee_12m_en_11"]


def errores_encuesta(panel: pd.DataFrame) -> pd.DataFrame:
    """Lo que esperaban los economistas a un año contra lo que pasó, fechado en el mes pronosticado."""
    esperado = panel["eee_12m_en_11"].shift(11)
    tabla = pd.DataFrame({"esperado": esperado, "real": panel["ipc_12m"]}).dropna()
    tabla["error"] = tabla["esperado"] - tabla["real"]
    return tabla
