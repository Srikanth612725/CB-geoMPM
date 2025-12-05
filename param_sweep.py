"""
Parameter sweep utility for the MPM validation model.

This script reuses the validation run helper and sweeps across parameter
combinations, persisting raw results and dimensionless groups to a Parquet
file (results_raw.parquet).
"""
import itertools
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from mpm_validation import EQUIVALENT_WIDTH, LIU_DATA, run_validation_simulation


SU_VALUES = [
    3_000,
    6_000,
    8_000,
    10_000,
    12_000,
    15_000,
    20_000,
    25_000,
    30_000,
    50_000,
]
WIDTH_VALUES = [5.0, EQUIVALENT_WIDTH, 8.0, 10.0]
THICKNESS_VALUES = [0.3, 0.5, 0.7, 1.0]
RATE_VALUES = [0.005, 0.01, 0.02, 0.05]
SERVICE_LOAD_KN = 2_000  # Example service load used for settlement estimation


def interpolate_settlement(loads: Iterable[float], settlements: Iterable[float], target_load: float) -> float:
    """Linear interpolation of settlement at the requested load.

    Returns NaN if the load is outside the simulated range or arrays are empty.
    """
    loads_arr = np.asarray(list(loads), dtype=float)
    settlements_arr = np.asarray(list(settlements), dtype=float)

    if loads_arr.size == 0 or settlements_arr.size == 0:
        return float("nan")

    if target_load < loads_arr.min() or target_load > loads_arr.max():
        return float("nan")

    return float(np.interp(target_load, loads_arr, settlements_arr))


def sweep_parameters():
    records = []

    for su, width, thickness, rate in itertools.product(
        SU_VALUES, WIDTH_VALUES, THICKNESS_VALUES, RATE_VALUES
    ):
        result = run_validation_simulation(
            su=su,
            width=width,
            thickness=thickness,
            rate=rate,
            target=0.5,
            interval=0.02,
            max_steps=12_000,
            plot_results=False,
        )

        ultimate_load = float(result["ultimate_load"])
        settlements = np.asarray(result["settlements"], dtype=float)
        loads = np.asarray(result["loads"], dtype=float)

        foundation_area = result["foundation_area"]
        soil_surface = result["soil_surface"]

        settlement_service = interpolate_settlement(loads, settlements, SERVICE_LOAD_KN)

        records.append(
            {
                "su": su,
                "width": width,
                "thickness": thickness,
                "rate": rate,
                "ultimate_load_kN": ultimate_load,
                "settlement_service_m": settlement_service,
                "B_over_H": width / soil_surface,
                "t_over_B": thickness / width,
                "q_ult_over_su": (ultimate_load * 1_000) / (su * foundation_area),
                "rate_times_B_over_cv": float("nan"),
                "settlements_m": settlements.tolist(),
                "loads_kN": loads.tolist(),
                "times_s": np.asarray(result["times"], dtype=float).tolist(),
            }
        )

    df = pd.DataFrame.from_records(records)
    output_path = Path(__file__).with_name("results_raw.parquet")
    df.to_parquet(output_path, index=False)
    return output_path


if __name__ == "__main__":
    path = sweep_parameters()
    print(f"Saved sweep results to {path}")
