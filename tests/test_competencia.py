import numpy as np
import pandas as pd
import pytest

from inflacion.aplicacion.competencia import ECONOMISTAS, Tarea, backtest, resumen
from inflacion.dominio.disponibilidad import informacion_al
from inflacion.dominio.metricas import diebold_mariano, mae
from inflacion.dominio.modelos import Ingenuo, MismoMesAnioAnterior, caracteristicas, ridge


def panel_falso(meses=200, semilla=1):
    rng = np.random.default_rng(semilla)
    idx = pd.date_range("2005-01-01", periods=meses, freq="MS")
    ipc = 0.3 + 0.2 * np.sin(2 * np.pi * idx.month / 12) + rng.normal(0, 0.1, meses)
    return pd.DataFrame(
        {
            "ipc_mensual": ipc,
            "ipc_12m": pd.Series(ipc, index=idx).rolling(12, min_periods=1).sum().to_numpy(),
            "dolar": 800 + rng.normal(0, 10, meses).cumsum(),
            "cobre": 3 + rng.normal(0, 0.05, meses).cumsum(),
            "tpm": 3 + rng.normal(0, 0.1, meses).cumsum(),
            "imacec": 100 + np.arange(meses) * 0.2,
            "eee_mes": ipc + rng.normal(0, 0.05, meses),
        },
        index=idx,
    )


def test_la_historia_termina_el_mes_anterior_y_respeta_el_rezago_del_imacec():
    panel = panel_falso()
    h = informacion_al(panel, pd.Timestamp("2010-06-01"), {"imacec": 2})
    assert h.index[-1] == pd.Timestamp("2010-05-01")
    assert pd.isna(h.at[pd.Timestamp("2010-05-01"), "imacec"])
    assert pd.notna(h.at[pd.Timestamp("2010-04-01"), "imacec"])


@pytest.mark.parametrize("pasos", [1, 12])
def test_ningun_modelo_ve_el_futuro(pasos):
    """Si cambio todo lo que pasó desde el mes de encuesta en adelante, el pronóstico no puede cambiar."""
    panel = panel_falso()
    origen = pd.Timestamp("2015-03-01")
    alterado = panel.copy()
    alterado.loc[origen:] = alterado.loc[origen:] * 50 + 999
    for modelo in (Ingenuo(), MismoMesAnioAnterior(), ridge()):
        a = modelo.pronosticar(informacion_al(panel, origen, {"imacec": 2}), "ipc_mensual", pasos)
        b = modelo.pronosticar(informacion_al(alterado, origen, {"imacec": 2}), "ipc_mensual", pasos)
        assert a == pytest.approx(b), modelo.nombre


def test_las_caracteristicas_del_mes_actual_usan_solo_datos_publicados():
    panel = panel_falso()
    h = informacion_al(panel, pd.Timestamp("2015-03-01"), {"imacec": 2})
    x, y = caracteristicas(h, "ipc_mensual", 1)
    assert x.index[-1] == pd.Timestamp("2015-03-01")
    assert x["ipc_mensual_l1"].iloc[-1] == panel.at[pd.Timestamp("2015-02-01"), "ipc_mensual"]
    assert pd.isna(y.iloc[-1])  # el valor que se pronostica no está en los datos de entrenamiento


def test_backtest_compara_con_la_encuesta_y_el_valor_real():
    panel = panel_falso()
    tarea = Tarea("mes", "ipc_mensual", 1, "eee_mes")
    r = backtest(panel, tarea, [Ingenuo()], {}, "2015-01-01")
    assert r.index[0] == pd.Timestamp("2015-01-01")
    assert r.at[pd.Timestamp("2015-01-01"), "real"] == panel.at[pd.Timestamp("2015-01-01"), "ipc_mensual"]
    assert (
        r.at[pd.Timestamp("2015-01-01"), "Ingenuo (último dato)"] == panel.at[pd.Timestamp("2014-12-01"), "ipc_mensual"]
    )
    tabla = resumen(r, tarea)
    eco = tabla[(tabla.periodo == "Todo") & (tabla.competidor == ECONOMISTAS)].iloc[0]
    assert eco.mae_vs_economistas == 1


def test_a_doce_meses_el_real_es_el_del_mes_pronosticado():
    panel = panel_falso().assign(eee_12m=3.0)
    r = backtest(panel, Tarea("12m", "ipc_12m", 12, "eee_12m"), [Ingenuo()], {}, "2015-01-01")
    fila = r.loc[pd.Timestamp("2015-01-01")]
    assert fila.mes_pronosticado == pd.Timestamp("2015-12-01")
    assert fila.real == panel.at[pd.Timestamp("2015-12-01"), "ipc_12m"]


def test_diebold_mariano_detecta_al_mejor_y_no_inventa_diferencias():
    rng = np.random.default_rng(0)
    bueno, malo = pd.Series(rng.normal(0, 1, 200)), pd.Series(rng.normal(0, 3, 200))
    estadistico, p = diebold_mariano(bueno, malo, 1)
    assert estadistico < 0 and p < 0.01
    # Dos pronosticadores igual de buenos: la diferencia no debería salir significativa.
    _, p_igual = diebold_mariano(bueno, pd.Series(rng.normal(0, 1, 200)), 1)
    assert p_igual > 0.05
    assert mae(pd.Series([-1.0, 1.0])) == 1.0
