"""Cómo se mide quién pronostica mejor."""

import numpy as np
import pandas as pd
from scipy import stats


def mae(errores: pd.Series) -> float:
    return float(np.mean(np.abs(errores)))


def rmse(errores: pd.Series) -> float:
    return float(np.sqrt(np.mean(np.square(errores))))


def diebold_mariano(errores_a: pd.Series, errores_b: pd.Series, horizonte: int) -> tuple[float, float]:
    """¿La diferencia de error entre A y B es real o puede ser suerte?

    Compara el error cuadrático de los dos en los mismos meses. Estadístico negativo = A se equivoca menos.
    Uso la corrección de Harvey, Leybourne y Newbold para muestras chicas, y la varianza considera que
    los pronósticos a más de un mes se traslapan (autocorrelación hasta horizonte - 1).
    Devuelve (estadístico, valor p a dos colas).
    """
    d = (np.square(errores_a) - np.square(errores_b)).dropna().to_numpy()
    n = len(d)
    if n < 10:
        return float("nan"), float("nan")
    media = d.mean()
    centrada = d - media
    var = centrada @ centrada / n
    for k in range(1, horizonte):
        var += 2 * (centrada[k:] @ centrada[:-k]) / n
    if var <= 0:
        return float("nan"), float("nan")
    dm = media / np.sqrt(var / n)
    correccion = np.sqrt((n + 1 - 2 * horizonte + horizonte * (horizonte - 1) / n) / n)
    estadistico = dm * correccion
    p = 2 * stats.t.sf(abs(estadistico), df=n - 1)
    return float(estadistico), float(p)
