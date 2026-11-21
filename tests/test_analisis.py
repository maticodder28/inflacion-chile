import numpy as np
import pandas as pd
import pytest

from inflacion.dominio.analisis import (
    acumulada_12m,
    coeficiente_traspaso,
    episodio_alto,
    errores_encuesta,
    estacionalidad,
    traspaso_dolar,
)

idx = pd.date_range("2018-01-01", periods=48, freq="MS")


def test_la_acumulada_compone_en_vez_de_sumar():
    mensual = pd.Series(1.0, index=idx)
    assert acumulada_12m(mensual).iloc[-1] == pytest.approx(100 * (1.01**12 - 1))  # 12,68%, no 12%


def test_episodio_alto_encuentra_el_tramo_mas_largo_y_su_peak():
    ipc = pd.Series([3, 5, 6, 3, 5, 7, 9, 8, 3] + [3] * 39, index=idx, dtype=float)
    e = episodio_alto(ipc)
    assert (e["meses"], e["peak"], e["mes_peak"]) == (4, 9.0, idx[6])
    assert episodio_alto(pd.Series(2.0, index=idx)) == {}


def test_estacionalidad_promedia_por_mes_calendario():
    mensual = pd.Series(np.where(idx.month == 3, 0.8, 0.2), index=idx)
    e = estacionalidad(mensual, "2018", "2021")
    assert e[3] == pytest.approx(0.8) and e[7] == pytest.approx(0.2)


def test_el_traspaso_detecta_el_rezago_correcto():
    # Si la inflación copia el alza del dólar con 6 meses de atraso, la correlación más alta tiene que estar en 6.
    rng = np.random.default_rng(3)
    largo = pd.date_range("2000-01-01", periods=240, freq="MS")
    dolar = pd.Series(700 * np.exp(rng.normal(0, 0.03, 240).cumsum()), index=largo)
    alza = 100 * (dolar / dolar.shift(12) - 1)
    panel = pd.DataFrame({"dolar": dolar, "ipc_12m": 3 + 0.1 * alza.shift(6)})
    t = traspaso_dolar(panel, 12)
    assert t.loc[t.correlacion.idxmax(), "rezago"] == 6
    assert coeficiente_traspaso(panel, 6) == pytest.approx(1.0, abs=1e-6)  # 0,1 pp por punto = 1 pp por cada 10%


def test_errores_encuesta_alinea_la_respuesta_con_el_mes_que_pronosticaba():
    panel = pd.DataFrame({"eee_12m_en_11": np.arange(48.0), "ipc_12m": 100.0}, index=idx)
    t = errores_encuesta(panel)
    assert t.index[0] == idx[11] and t["esperado"].iloc[0] == 0.0 and t["error"].iloc[0] == -100.0
