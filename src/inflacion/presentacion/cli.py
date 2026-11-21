"""Línea de comandos: python -m inflacion <comando>. Acá se arman las dependencias reales."""

import argparse
import os
from pathlib import Path

from inflacion.aplicacion.catalogo import actualizar_catalogo
from inflacion.dominio.series import Frecuencia
from inflacion.infraestructura.almacen_csv import AlmacenCSV
from inflacion.infraestructura.bcch import ClienteBCCh

DATA = Path(__file__).resolve().parents[3] / "data"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="inflacion")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("catalogo", help="Baja el catálogo de series del Banco Central a data/catalogo.csv")
    args = parser.parse_args(argv)

    if args.comando == "catalogo":
        cliente = ClienteBCCh(os.environ.get("BCCH_TOKEN", ""))
        series = actualizar_catalogo(cliente, AlmacenCSV(DATA), [Frecuencia.DIARIA, Frecuencia.MENSUAL])
        print(f"Catálogo guardado: {len(series)} series en {DATA / 'catalogo.csv'}")
