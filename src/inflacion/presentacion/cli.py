"""Línea de comandos: python -m inflacion <comando>. Acá se arman las dependencias reales."""

import argparse
import os
from datetime import date
from pathlib import Path

from inflacion.aplicacion.catalogo import actualizar_catalogo
from inflacion.aplicacion.descarga import descargar_panel
from inflacion.dominio.series import Frecuencia
from inflacion.infraestructura.almacen_csv import AlmacenCSV
from inflacion.infraestructura.bcch import ClienteBCCh
from inflacion.infraestructura.config import leer_series

RAIZ = Path(__file__).resolve().parents[3]
DATA = RAIZ / "data"
# Desde 2001 hay encuesta de expectativas; parto en 2000 para tener rezagos.
DESDE = date(2000, 1, 1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="inflacion")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("catalogo", help="Baja el catálogo de series del Banco Central a data/catalogo.csv")
    sub.add_parser("datos", help="Baja las series de config/series.toml y arma data/panel_mensual.csv")
    args = parser.parse_args(argv)

    cliente = ClienteBCCh(os.environ.get("BCCH_TOKEN", ""))
    almacen = AlmacenCSV(DATA)
    if args.comando == "catalogo":
        series = actualizar_catalogo(cliente, almacen, [Frecuencia.DIARIA, Frecuencia.MENSUAL])
        print(f"Catálogo guardado: {len(series)} series")
    elif args.comando == "datos":
        panel = descargar_panel(cliente, almacen, leer_series(RAIZ / "config" / "series.toml"), DESDE, date.today())
        print(f"Panel guardado: {len(panel)} meses x {panel.shape[1]} series, hasta {panel.index.max():%Y-%m}")
        print(panel.notna().sum().to_string())
