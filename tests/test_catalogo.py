import pytest

from inflacion.aplicacion.catalogo import actualizar_catalogo
from inflacion.dominio.series import Frecuencia, InfoSerie
from inflacion.infraestructura.bcch import ClienteBCCh, ErrorBCCh


class SesionFalsa:
    """Responde como la API del Banco Central, sin red."""

    def __init__(self, respuesta: dict):
        self.respuesta = respuesta
        self.pedidos: list[dict] = []

    def get(self, url, params, timeout):
        self.pedidos.append(params)
        respuesta = self.respuesta

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return respuesta

        return R()


CATALOGO = {
    "Codigo": 0,
    "Descripcion": "Success",
    "SeriesInfos": [
        {
            "seriesId": "F073.TCO.PRE.Z.D",
            "spanishTitle": " Tipo de cambio nominal (dólar observado) ",
            "firstObservation": "1984-01-02",
            "lastObservation": "2026-11-20",
        },
    ],
}


def test_el_cliente_lee_el_catalogo_y_manda_el_token():
    sesion = SesionFalsa(CATALOGO)
    series = ClienteBCCh("tok", sesion=sesion, pausa_s=0).catalogo(Frecuencia.DIARIA)
    assert series == [
        InfoSerie(
            "F073.TCO.PRE.Z.D",
            "Tipo de cambio nominal (dólar observado)",
            Frecuencia.DIARIA,
            "1984-01-02",
            "2026-11-20",
        )
    ]
    assert sesion.pedidos[0] == {"token": "tok", "function": "SearchSeries", "frequency": "DAILY"}


def test_un_error_de_la_api_no_pasa_en_silencio():
    # La API responde HTTP 200 aunque el token esté malo; el error viene en el JSON.
    sesion = SesionFalsa({"Codigo": -5, "Descripcion": "Invalid username or password"})
    with pytest.raises(ErrorBCCh, match="-5"):
        ClienteBCCh("malo", sesion=sesion, pausa_s=0).catalogo(Frecuencia.MENSUAL)


def test_sin_token_avisa_antes_de_llamar():
    with pytest.raises(ErrorBCCh, match="BCCH_TOKEN"):
        ClienteBCCh("")


def test_actualizar_catalogo_junta_frecuencias_y_ordena():
    class Fuente:
        def catalogo(self, f):
            return [InfoSerie(c, c, f, None, None) for c in ("B", "A")]

    class Almacen:
        guardado: list = []

        def guardar_catalogo(self, series):
            Almacen.guardado = series

    series = actualizar_catalogo(Fuente(), Almacen(), [Frecuencia.MENSUAL, Frecuencia.DIARIA])
    assert [(s.frecuencia.value, s.codigo) for s in series] == [
        ("DAILY", "A"),
        ("DAILY", "B"),
        ("MONTHLY", "A"),
        ("MONTHLY", "B"),
    ]
    assert Almacen.guardado == series
