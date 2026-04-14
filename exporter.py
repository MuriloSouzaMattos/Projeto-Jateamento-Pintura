from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

EXPORT_DIR = Path(r"\\ad101.siemens-energy.net\dfs\EnergyFS\LATAM\TICA_PRD\PRD\JAT\D4C\App_Elcometer_Exportacao")


def posto_suffix(posto: str) -> str:
    # posto interno: FUNDO / ACAB / JAT
    if posto == "FUNDO":
        return "FUNDO"
    if posto == "ACAB":
        return "ACAB"
    if posto == "JAT":
        return "JAT"
    return posto


def next_available_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    n = 2
    while True:
        cand = base.with_name(f"{stem}_{n}{suffix}")
        if not cand.exists():
            return cand
        n += 1


def export_measurement_to_excel(
    *,
    serie: str,
    projeto: str,
    operador: str,
    varal: str,
    posto: str,
    created_at: str,
    values: list[str],  # 46
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    suf = posto_suffix(posto)
    base = EXPORT_DIR / f"{serie}_{suf}.xlsx"
    path = next_available_path(base)

    row = {
        "Data/Hora Cadastro": created_at,
        "Data/Hora Export": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Projeto": projeto,
        "Número de Série": serie,
        "Operador": operador,
        "Varal": varal,
        "Posto": posto,
    }
    for i in range(46):
        row[f"M{i+1:02d}"] = values[i]

    df = pd.DataFrame([row])
    df.to_excel(str(path), index=False, sheet_name="Medições")
    return path