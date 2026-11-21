"""Los competidores. Todos reciben lo mismo: la historia tal como se veía el día de la encuesta
(ver disponibilidad.py) y devuelven un solo número, el pronóstico para `pasos` meses después del último dato.

Agregar un modelo nuevo es escribir una clase con `nombre` y `pronosticar`; la competencia no cambia.
"""

import warnings
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import pandas as pd


class Modelo(Protocol):
    nombre: str

    def pronosticar(self, historia: pd.DataFrame, objetivo: str, pasos: int) -> float: ...


# ---------------------------------------------------------------------
# Referencias simples. Si un modelo "inteligente" no les gana, no sirve.
# ---------------------------------------------------------------------
@dataclass
class Ingenuo:
    """Lo último que se conoce se repite."""

    nombre: str = "Ingenuo (último dato)"

    def pronosticar(self, historia, objetivo, pasos):
        return float(historia[objetivo].dropna().iloc[-1])


@dataclass
class MismoMesAnioAnterior:
    """El mismo mes del año pasado. Captura la estacionalidad del IPC (marzo, por ejemplo, siempre sube)."""

    nombre: str = "Mismo mes año anterior"

    def pronosticar(self, historia, objetivo, pasos):
        return float(historia[objetivo].iloc[pasos - 13])


@dataclass
class Constante:
    """Un valor fijo, como la meta de inflación del Banco Central (3%)."""

    valor: float = 3.0
    nombre: str = "Meta del Banco Central (3%)"

    def pronosticar(self, historia, objetivo, pasos):
        return self.valor


# ---------------------------------------------------------------------
# Series de tiempo clásico
# ---------------------------------------------------------------------
@dataclass
class Sarima:
    """SARIMA sobre la propia serie. Ajusto con los últimos `ventana` meses para que se adapte a cambios de régimen."""

    orden: tuple[int, int, int] = (1, 0, 1)
    estacional: tuple[int, int, int, int] = (1, 0, 0, 12)
    ventana: int = 180
    nombre: str = "SARIMA"

    def pronosticar(self, historia, objetivo, pasos):
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        y = historia[objetivo].dropna().iloc[-self.ventana :]
        y = y.asfreq("MS")
        with warnings.catch_warnings():
            # Los avisos de convergencia no cambian el resultado y ensucian la salida del backtest.
            warnings.simplefilter("ignore")
            ajuste = SARIMAX(y, order=self.orden, seasonal_order=self.estacional, trend="c").fit(disp=False)
        return float(ajuste.forecast(pasos).iloc[-1])


# ---------------------------------------------------------------------
# Machine learning con las demás variables
# ---------------------------------------------------------------------
def _log_var(s: pd.Series, k: int) -> pd.Series:
    """Variación porcentual aproximada en k meses, con logaritmos (simétrica para alzas y bajas)."""
    return 100 * np.log(s / s.shift(k))


def caracteristicas(historia: pd.DataFrame, objetivo: str, pasos: int) -> tuple[pd.DataFrame, pd.Series]:
    """Arma X e y para un modelo de pronóstico directo.

    X se indexa por mes de encuesta s y usa solo datos de s-1 hacia atrás (s-2 para el Imacec).
    y(s) es el objetivo `pasos` meses después del último dato: el mes s + pasos - 1.
    La última fila de X es la del mes de encuesta actual, que todavía no tiene y: esa es la que se pronostica.
    """
    h = historia.copy()
    h.loc[h.index[-1] + pd.offsets.MonthBegin(1)] = np.nan  # fila del mes de encuesta actual
    ipc = h["ipc_mensual"]
    x = pd.DataFrame(index=h.index)
    for k in (1, 2, 3, 12):
        x[f"ipc_mensual_l{k}"] = ipc.shift(k)
    x["ipc_12m_l1"] = h["ipc_12m"].shift(1)
    x["ipc_12m_cambio_3m"] = h["ipc_12m"].shift(1) - h["ipc_12m"].shift(4)
    x["dolar_var_1m"] = _log_var(h["dolar"], 1).shift(1)
    x["dolar_var_12m"] = _log_var(h["dolar"], 12).shift(1)
    x["cobre_var_12m"] = _log_var(h["cobre"], 12).shift(1)
    x["tpm_l1"] = h["tpm"].shift(1)
    x["tpm_cambio_12m"] = (h["tpm"] - h["tpm"].shift(12)).shift(1)
    x["imacec_var_12m"] = _log_var(h["imacec"], 12).shift(2)
    # Mes calendario del objetivo, como seno y coseno para que diciembre quede cerca de enero.
    mes_objetivo = (x.index + pd.DateOffset(months=pasos - 1)).month
    x["mes_sin"] = np.sin(2 * np.pi * mes_objetivo / 12)
    x["mes_cos"] = np.cos(2 * np.pi * mes_objetivo / 12)
    y = h[objetivo].shift(-(pasos - 1))
    return x, y


@dataclass
class Directo:
    """Pronóstico directo con un estimador de scikit-learn: aprende de los meses pasados cómo se relacionan
    las variables de hoy con el objetivo `pasos` meses después."""

    nombre: str
    crear: object = field(repr=False)  # función sin argumentos que devuelve un estimador nuevo
    minimo: int = 60  # meses de entrenamiento mínimos

    def pronosticar(self, historia, objetivo, pasos):
        x, y = caracteristicas(historia, objetivo, pasos)
        actual = x.iloc[[-1]]
        entrenamiento = x.iloc[:-1].assign(y=y.iloc[:-1]).dropna()
        if len(entrenamiento) < self.minimo or actual.isna().any(axis=None):
            return float("nan")
        estimador = self.crear()
        estimador.fit(entrenamiento.drop(columns="y"), entrenamiento["y"])
        return float(estimador.predict(actual)[0])


def ridge() -> Directo:
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return Directo("Regresión ridge", lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20))))


def gradient_boosting() -> Directo:
    from sklearn.ensemble import HistGradientBoostingRegressor

    # Pocos datos (unos 250 meses): árboles chicos y aprendizaje lento para no memorizar.
    return Directo(
        "Gradient boosting",
        lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, random_state=0),
    )
