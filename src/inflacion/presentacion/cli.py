"""Línea de comandos: python -m inflacion <comando>. Acá se arman las dependencias reales."""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from inflacion.aplicacion.catalogo import actualizar_catalogo
from inflacion.aplicacion.competencia import ECONOMISTAS, Tarea, competir
from inflacion.aplicacion.descarga import descargar_panel
from inflacion.dominio import analisis
from inflacion.dominio.modelos import Constante, Ingenuo, MismoMesAnioAnterior, Sarima, gradient_boosting, ridge
from inflacion.dominio.series import Frecuencia
from inflacion.infraestructura.almacen_csv import AlmacenCSV
from inflacion.infraestructura.bcch import ClienteBCCh
from inflacion.infraestructura.config import leer_series
from inflacion.presentacion import graficos

RAIZ = Path(__file__).resolve().parents[3]
DATA = RAIZ / "data"
# Desde 2001 hay encuesta de expectativas; parto en 2000 para tener rezagos.
DESDE = date(2000, 1, 1)
# La competencia parte en 2010: antes hay muy pocos años para entrenar los modelos.
DESDE_COMPETENCIA = "2010-01-01"


def tareas():
    """Las dos preguntas del proyecto y quién compite en cada una."""
    return [
        (
            Tarea("Inflación del mes", "ipc_mensual", 1, "eee_mes"),
            [Ingenuo(), MismoMesAnioAnterior(), Sarima(), ridge(), gradient_boosting()],
        ),
        (
            Tarea("Inflación en 12 meses, a un año", "ipc_12m", 12, "eee_12m_en_11"),
            [Ingenuo(), Constante(), Sarima(orden=(2, 0, 0), estacional=(0, 0, 0, 0)), ridge(), gradient_boosting()],
        ),
    ]


def dibujar_graficos(panel: pd.DataFrame, resumen: pd.DataFrame) -> list[Path]:
    carpeta = RAIZ / "docs" / "img"
    return [
        graficos.inflacion_historica(panel["ipc_12m"], analisis.episodio_alto(panel["ipc_12m"]), carpeta),
        graficos.general_vs_subyacente(panel["ipc_12m"], analisis.acumulada_12m(panel["ipc_sae_mensual"]), carpeta),
        graficos.estacionalidad(analisis.estacionalidad(panel["ipc_mensual"], "2010", "2019"), carpeta),
        graficos.tasa_e_inflacion(panel["ipc_12m"], panel["tpm"], carpeta),
        graficos.esperado_vs_real(analisis.errores_encuesta(panel), carpeta),
        graficos.resultados(resumen, carpeta, ECONOMISTAS),
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="inflacion")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("catalogo", help="Baja el catálogo de series del Banco Central a data/catalogo.csv")
    sub.add_parser("datos", help="Baja las series de config/series.toml y arma data/panel_mensual.csv")
    sub.add_parser("competir", help="Corre la competencia modelos vs economistas y guarda data/resultados/")
    sub.add_parser("graficos", help="Dibuja los gráficos del análisis en docs/img/")
    args = parser.parse_args(argv)

    almacen = AlmacenCSV(DATA)
    if args.comando == "graficos":
        dibujar_graficos(almacen.leer_panel(), pd.read_csv(DATA / "resultados" / "resumen.csv"))
        return
    if args.comando == "competir":
        defs = leer_series(RAIZ / "config" / "series.toml")
        # El avance se muestra solo en una terminal; en GitHub Actions llenaría el log.
        avance = (
            (lambda t, i, n: print(f"  {t.nombre}: {i}/{n}", end="\r", flush=True)) if sys.stdout.isatty() else None
        )
        tabla = competir(almacen, tareas(), {d.nombre: d.rezago for d in defs}, DESDE_COMPETENCIA, avance)
        todo = tabla[tabla.periodo == "Todo"][["tarea", "competidor", "meses", "mae", "mae_vs_economistas", "p_valor"]]
        print("\n" + todo.round(3).to_string(index=False))
        return

    cliente = ClienteBCCh(os.environ.get("BCCH_TOKEN", ""))
    if args.comando == "catalogo":
        series = actualizar_catalogo(cliente, almacen, [Frecuencia.DIARIA, Frecuencia.MENSUAL])
        print(f"Catálogo guardado: {len(series)} series")
    elif args.comando == "datos":
        panel = descargar_panel(cliente, almacen, leer_series(RAIZ / "config" / "series.toml"), DESDE, date.today())
        print(f"Panel guardado: {len(panel)} meses x {panel.shape[1]} series, hasta {panel.index.max():%Y-%m}")
        print(panel.notna().sum().to_string())
