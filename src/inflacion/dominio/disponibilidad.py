"""Qué se sabía en cada momento. Es lo más importante del proyecto: si un modelo ve datos que todavía no
existían cuando los economistas respondieron la encuesta, la comparación es trampa.

La Encuesta de Expectativas se responde cerca del día 10 del mes t. Para entonces ya salió el IPC de t-1
(se publica el día 8), el dólar y la tasa del mes anterior completos, y el Imacec de t-2.
"""

import pandas as pd


def informacion_al(panel: pd.DataFrame, origen: pd.Timestamp, rezagos: dict[str, int]) -> pd.DataFrame:
    """El panel tal como se veía al momento de la encuesta del mes `origen`.

    Corta en el mes anterior y borra lo que todavía no se publicaba según el rezago de cada serie.
    """
    historia = panel.loc[: origen - pd.offsets.MonthBegin(1)].copy()
    for columna, rezago in rezagos.items():
        if columna in historia and rezago > 1:
            historia.iloc[-(rezago - 1) :, historia.columns.get_loc(columna)] = float("nan")
    return historia
