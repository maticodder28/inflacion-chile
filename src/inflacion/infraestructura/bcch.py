"""Cliente de la API REST del Banco Central de Chile (BDE).

Uso el endpoint REST directo con requests en vez de la librería bcchapi: son dos llamadas y así
puedo probarlo con una sesión falsa. El token sale de la variable de entorno BCCH_TOKEN; nunca va en el código.
"""

import time

import requests

from inflacion.dominio.series import Frecuencia, InfoSerie

URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
# Los términos de uso piden máximo 5 consultas por segundo; con 0,25 s entre llamadas quedo bajo eso.
PAUSA_S = 0.25


class ErrorBCCh(RuntimeError):
    pass


class ClienteBCCh:
    def __init__(self, token: str, sesion: requests.Session | None = None, pausa_s: float = PAUSA_S):
        if not token:
            raise ErrorBCCh("Falta el token de la API (variable BCCH_TOKEN).")
        self._token = token
        self._sesion = sesion or requests.Session()
        self._pausa_s = pausa_s

    def _get(self, **params: str) -> dict:
        time.sleep(self._pausa_s)
        r = self._sesion.get(URL, params={"token": self._token, **params}, timeout=60)
        r.raise_for_status()
        datos = r.json()
        # La API responde 200 incluso con error; el detalle viene en Codigo y Descripcion.
        if datos.get("Codigo", 0) != 0:
            raise ErrorBCCh(f"La API respondió {datos.get('Codigo')}: {datos.get('Descripcion')}")
        return datos

    def catalogo(self, frecuencia: Frecuencia) -> list[InfoSerie]:
        datos = self._get(function="SearchSeries", frequency=frecuencia.value)
        return [
            InfoSerie(
                codigo=s["seriesId"],
                titulo=(s.get("spanishTitle") or s.get("englishTitle") or "").strip(),
                frecuencia=frecuencia,
                primera=s.get("firstObservation"),
                ultima=s.get("lastObservation"),
            )
            for s in datos.get("SeriesInfos") or []
        ]
