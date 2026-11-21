from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from inflacion.aplicacion.descarga import descargar_panel
from inflacion.dominio.series import DefSerie, a_mensual, empalmar
from inflacion.infraestructura.bcch import ClienteBCCh
from inflacion.infraestructura.config import leer_series
from tests.test_catalogo import SesionFalsa


def s(fechas, valores):
    return pd.Series(valores, index=pd.to_datetime(fechas), dtype=float)


def test_empalmar_usa_el_tramo_nuevo_donde_se_traslapan():
    vieja = s(["2022-11-01", "2022-12-01", "2023-01-01"], [1.0, 2.0, 3.0])
    nueva = s(["2023-01-01", "2023-02-01"], [30.0, 40.0])
    assert empalmar([vieja, nueva]).tolist() == [1.0, 2.0, 30.0, 40.0]


def test_a_mensual_promedia_o_toma_el_ultimo_y_fecha_el_primero_del_mes():
    diaria = s(["2024-01-02", "2024-01-31", "2024-02-15"], [900.0, 920.0, 950.0])
    assert a_mensual(diaria, "promedio").to_dict() == {
        pd.Timestamp("2024-01-01"): 910.0,
        pd.Timestamp("2024-02-01"): 950.0,
    }
    assert a_mensual(diaria, "ultimo").iloc[0] == 920.0


def test_def_serie_rechaza_configuraciones_malas():
    with pytest.raises(ValueError):
        DefSerie("x", "x", ())
    with pytest.raises(ValueError):
        DefSerie("x", "x", ("A",), agregacion="mediana")


def test_el_cliente_lee_observaciones_y_descarta_las_faltantes():
    respuesta = {
        "Codigo": 0,
        "Series": {
            "Obs": [
                {"indexDateString": "02-01-2024", "value": "880.5", "statusCode": "OK"},
                {"indexDateString": "03-01-2024", "value": "NaN", "statusCode": "ND"},
            ]
        },
    }
    serie = ClienteBCCh("tok", sesion=SesionFalsa(respuesta), pausa_s=0).observaciones(
        "F073.TCO.PRE.Z.D", date(2024, 1, 1), date(2024, 1, 31)
    )
    assert serie.to_dict() == {pd.Timestamp("2024-01-02"): 880.5}


def test_descargar_panel_empalma_mensualiza_y_guarda():
    datos = {
        "A1": s(["2024-01-01"], [1.0]),
        "A2": s(["2024-02-01"], [2.0]),
        "D": s(["2024-01-05", "2024-01-20", "2024-02-10"], [10.0, 20.0, 30.0]),
    }

    class Fuente:
        def observaciones(self, codigo, desde, hasta):
            return datos[codigo]

    class Almacen:
        panel = None

        def guardar_panel(self, panel):
            Almacen.panel = panel

    defs = [DefSerie("a", "a", ("A1", "A2")), DefSerie("d", "d", ("D",), "promedio")]
    panel = descargar_panel(Fuente(), Almacen(), defs, date(2024, 1, 1), date(2024, 3, 1))
    assert panel.to_dict("list") == {"a": [1.0, 2.0], "d": [15.0, 30.0]}
    assert Almacen.panel is panel


def test_la_configuracion_del_repo_es_valida():
    defs = leer_series(Path(__file__).resolve().parents[1] / "config" / "series.toml")
    assert len({d.nombre for d in defs}) == len(defs)
