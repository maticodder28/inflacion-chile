"""Los gráficos del análisis, con un estilo común. Reciben datos ya calculados (dominio/analisis.py) y solo dibujan.

Reglas que sigo: un solo eje Y por gráfico, líneas de 2 px, grilla tenue, etiquetas directas al final de cada
serie (además de la leyenda) y los colores siempre en el mismo orden: azul = inflación real, naranjo = economistas.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402

from inflacion.dominio.analisis import RANGO_META  # noqa: E402

AZUL, NARANJO, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
FONDO, TEXTO, TEXTO_2, GRILLA, BANDA = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0", "#efeee9"
FUENTE = "Fuente: Banco Central de Chile (BDE). Elaboración propia."


def num(v: float, decimales: int = 1) -> str:
    """Número con coma decimal, como se escribe en Chile."""
    return f"{v:.{decimales}f}".replace(".", ",")


def _estilo():
    plt.rcParams.update(
        {
            "figure.facecolor": FONDO,
            "axes.facecolor": FONDO,
            "axes.edgecolor": GRILLA,
            "axes.labelcolor": TEXTO_2,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRILLA,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "xtick.color": TEXTO_2,
            "ytick.color": TEXTO_2,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "font.size": 11,
            "font.family": "DejaVu Sans",
            "legend.frameon": False,
            "axes.axisbelow": True,  # la grilla va detrás de las barras y líneas
        }
    )


def _figura(titulo: str, subtitulo: str, ancho=10, alto=5):
    _estilo()
    fig, ax = plt.subplots(figsize=(ancho, alto))
    fig.text(0.01, 0.97, titulo, fontsize=15, fontweight="bold", color=TEXTO, va="top")
    fig.text(0.01, 0.91, subtitulo, fontsize=11, color=TEXTO_2, va="top")
    fig.text(0.01, 0.01, FUENTE, fontsize=8.5, color=TEXTO_2)
    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.06, right=0.9)
    return fig, ax


def _etiqueta_final(ax, serie: pd.Series, texto: str, color: str, dy=0):
    """Etiqueta directa al final de la línea, en tinta de texto con una marca del color de la serie."""
    s = serie.dropna()
    x, y = s.index[-1], s.iloc[-1]
    ax.plot([x], [y], "o", color=color, ms=6, mec=FONDO, mew=2, zorder=5)
    ax.annotate(
        f"{texto} {num(y)}%", (x, y), xytext=(8, dy), textcoords="offset points", va="center", color=TEXTO, fontsize=10
    )


def _guardar(fig, carpeta: Path, nombre: str) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.png"
    fig.savefig(ruta, dpi=160, facecolor=FONDO)
    plt.close(fig)
    return ruta


def _fechas(ax, cada_anios=2):
    ax.xaxis.set_major_locator(mdates.YearLocator(cada_anios))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    # Ticks cada 2 puntos: con el automático salen cada 2,5 y al redondear quedan mal rotulados.
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")


def inflacion_historica(ipc_12m: pd.Series, episodio: dict, carpeta: Path) -> Path:
    fig, ax = _figura(
        "Inflación en Chile, 2000–2026",
        "IPC, variación en 12 meses. La franja es el rango meta del Banco Central (2% a 4%).",
    )
    ax.axhspan(*RANGO_META, color=BANDA, zorder=0, lw=0)
    ax.plot(ipc_12m.index, ipc_12m, color=AZUL, lw=2)
    if episodio:
        peak = f"Peak: {num(episodio['peak'])}% ({episodio['mes_peak']:%m-%Y})"
        texto = f"{peak}\n{episodio['meses']} meses seguidos sobre 4%"
        ax.annotate(
            texto,
            (episodio["mes_peak"], episodio["peak"]),
            xytext=(-170, -18),
            textcoords="offset points",
            color=TEXTO,
            fontsize=10,
            arrowprops={"arrowstyle": "-", "color": TEXTO_2, "lw": 0.8},
        )
    _etiqueta_final(ax, ipc_12m, "Último:", AZUL)
    _fechas(ax)
    return _guardar(fig, carpeta, "01_inflacion_historica")


def general_vs_subyacente(ipc_12m: pd.Series, sae_12m: pd.Series, carpeta: Path) -> Path:
    desde = sae_12m.first_valid_index()
    fig, ax = _figura(
        "La inflación general frente a la subyacente",
        "Variación en 12 meses. El IPC SAE excluye alimentos y energía, que son los precios más volátiles.",
    )
    ax.axhspan(*RANGO_META, color=BANDA, zorder=0, lw=0)
    g = ipc_12m.loc[desde:]
    ax.plot(g.index, g, color=AZUL, lw=2, label="IPC general")
    ax.plot(sae_12m.index, sae_12m, color=AQUA, lw=2, label="IPC sin alimentos ni energía (SAE)")
    _etiqueta_final(ax, g, "General", AZUL, dy=7)
    _etiqueta_final(ax, sae_12m, "SAE", AQUA, dy=-7)
    ax.legend(loc="upper left", fontsize=10)
    _fechas(ax, 1)
    return _guardar(fig, carpeta, "02_general_vs_subyacente")


def estacionalidad(promedios: pd.Series, carpeta: Path) -> Path:
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    fig, ax = _figura(
        "Los meses en que más suben los precios",
        "Inflación mensual promedio por mes, 2010–2019 (años sin shocks grandes).",
    )
    barras = ax.bar(meses, promedios.reindex(range(1, 13)), color=AZUL, width=0.6)
    for b in barras:
        ax.annotate(
            num(b.get_height(), 2),
            (b.get_x() + b.get_width() / 2, b.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color=TEXTO_2,
        )
    ax.yaxis.set_major_formatter(lambda v, _: f"{num(v)}%")
    return _guardar(fig, carpeta, "03_estacionalidad")


def tasa_e_inflacion(ipc_12m: pd.Series, tpm: pd.Series, carpeta: Path, desde="2015-01-01") -> Path:
    fig, ax = _figura(
        "Cómo respondió el Banco Central",
        "Tasa de política monetaria e inflación en 12 meses. Las dos están en %, así que comparten eje.",
    )
    ax.axhspan(*RANGO_META, color=BANDA, zorder=0, lw=0)
    i, t = ipc_12m.loc[desde:], tpm.loc[desde:]
    ax.plot(i.index, i, color=AZUL, lw=2, label="Inflación 12 meses")
    ax.plot(t.index, t, color=NARANJO, lw=2, label="Tasa de política monetaria")
    _etiqueta_final(ax, i, "Inflación", AZUL, dy=7)
    _etiqueta_final(ax, t, "Tasa", NARANJO, dy=-7)
    ax.legend(loc="upper left", fontsize=10)
    _fechas(ax, 1)
    return _guardar(fig, carpeta, "04_tasa_e_inflacion")


def esperado_vs_real(tabla: pd.DataFrame, carpeta: Path, desde="2010-01-01") -> Path:
    fig, ax = _figura(
        "Lo que esperaban los economistas vs. lo que pasó",
        "Inflación en 12 meses. La línea naranja es lo que la encuesta esperaba para ese mes, un año antes.",
    )
    ax.axhspan(*RANGO_META, color=BANDA, zorder=0, lw=0)
    t = tabla.loc[desde:]
    ax.plot(t.index, t["real"], color=AZUL, lw=2, label="Inflación real")
    ax.plot(t.index, t["esperado"], color=NARANJO, lw=2, label="Esperada un año antes (encuesta)")
    peor = t["error"].idxmin()
    ax.annotate(
        f"{peor:%m-%Y}: esperaban {num(t.at[peor, 'esperado'])}%,\nfue {num(t.at[peor, 'real'])}%",
        (peor, t.at[peor, "real"]),
        xytext=(-185, -10),
        textcoords="offset points",
        color=TEXTO,
        fontsize=10,
        arrowprops={"arrowstyle": "-", "color": TEXTO_2, "lw": 0.8},
    )
    ax.legend(loc="upper left", fontsize=10)
    _fechas(ax, 2)
    return _guardar(fig, carpeta, "05_esperado_vs_real")


def resultados(resumen: pd.DataFrame, carpeta: Path, economistas: str) -> Path:
    """Error promedio de cada competidor, una tarea por panel (escalas distintas, así que no comparten eje)."""
    _estilo()
    todo = resumen[resumen["periodo"] == "Todo"]
    tareas = list(todo["tarea"].unique())
    fig, ejes = plt.subplots(1, len(tareas), figsize=(12, 5))
    fig.text(0.01, 0.97, "¿Le gana un modelo a los economistas?", fontsize=15, fontweight="bold", color=TEXTO, va="top")
    fig.text(
        0.01,
        0.91,
        "Error absoluto medio de cada pronóstico, 2010–2026 (puntos porcentuales; más corto es mejor).",
        fontsize=11,
        color=TEXTO_2,
        va="top",
    )
    fig.text(
        0.01,
        0.01,
        FUENTE + " * = diferencia con los economistas estadísticamente significativa (p < 0,05).",
        fontsize=8.5,
        color=TEXTO_2,
    )
    for ax, tarea in zip(ejes, tareas, strict=True):
        t = todo[todo["tarea"] == tarea].sort_values("mae", ascending=False)
        colores = [NARANJO if c == economistas else AZUL for c in t["competidor"]]
        ax.barh(t["competidor"], t["mae"], color=colores, height=0.55)
        ax.set_title(tarea, loc="left", fontsize=12, color=TEXTO, pad=10)
        ax.grid(axis="x", color=GRILLA)
        ax.grid(axis="y", visible=False)
        for y, (_, fila) in enumerate(t.iterrows()):
            marca = " *" if fila["p_valor"] < 0.05 else ""
            ax.annotate(
                f"{num(fila['mae'], 2)}{marca}",
                (fila["mae"], y),
                xytext=(4, 0),
                textcoords="offset points",
                va="center",
                fontsize=9.5,
                color=TEXTO,
            )
        ax.set_xlim(0, t["mae"].max() * 1.25)
        ax.xaxis.set_major_formatter(lambda v, _: num(v))
    fig.subplots_adjust(top=0.8, bottom=0.12, left=0.17, right=0.98, wspace=0.75)
    return _guardar(fig, carpeta, "06_resultados")
