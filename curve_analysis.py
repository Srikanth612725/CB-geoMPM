"""
Utility functions for processing load–displacement curves and summarising runs.

Features
--------
* Parse curve files (CSV or Parquet) with displacement and load columns.
* Smooth noisy data using a centered rolling average.
* Resample curves onto a consistent displacement spacing for fair comparisons.
* Compute peak load, displacement at peak, secant stiffness at service load,
  and ductility ratio (peak displacement relative to service displacement).
* Summarise multiple runs into a single Parquet file keyed by parameter set.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import json

import numpy as np
import pandas as pd


@dataclass
class LoadDisplacementMetrics:
    """Computed metrics for a single load–displacement curve."""

    peak_load: float
    displacement_at_peak: float
    secant_stiffness: float
    ductility_ratio: float


def _get_columns(df: pd.DataFrame, displacement_column: Optional[str], load_column: Optional[str]) -> Tuple[pd.Series, pd.Series]:
    """Return displacement and load series from ``df``.

    Args:
        df: DataFrame containing the curve data.
        displacement_column: Explicit displacement column name. If ``None``,
            common aliases are probed in order.
        load_column: Explicit load column name. If ``None``, common aliases
            are probed in order.

    Raises:
        KeyError: If either column cannot be resolved.
    """

    displacement_candidates = [displacement_column] if displacement_column else [
        "displacement",
        "settlement",
        "u",
    ]
    load_candidates = [load_column] if load_column else [
        "load",
        "reaction",
        "force",
    ]

    displacement_name = next((c for c in displacement_candidates if c in df.columns), None)
    load_name = next((c for c in load_candidates if c in df.columns), None)

    if displacement_name is None or load_name is None:
        missing = []
        if displacement_name is None:
            missing.append(f"displacement column not found (candidates: {displacement_candidates})")
        if load_name is None:
            missing.append(f"load column not found (candidates: {load_candidates})")
        raise KeyError("; ".join(missing))

    return df[displacement_name].astype(float), df[load_name].astype(float)


def smooth_curve(loads: Iterable[float], window: int = 5) -> np.ndarray:
    """Apply a centered rolling-average to reduce noise.

    The window is clipped to the length of the data to avoid empty results.
    """

    series = pd.Series(loads, dtype=float)
    window = max(1, min(window, len(series)))
    return series.rolling(window=window, center=True, min_periods=1).mean().to_numpy()


def resample_curve(displacements: Iterable[float], loads: Iterable[float], spacing: float) -> Tuple[np.ndarray, np.ndarray]:
    """Resample the curve onto a uniform displacement grid.

    Args:
        displacements: Original displacement values (assumed sortable).
        loads: Load values aligned with ``displacements``.
        spacing: Target spacing for the uniform grid.

    Returns:
        Tuple of (resampled_displacements, interpolated_loads).
    """

    disp = np.asarray(displacements, dtype=float)
    load = np.asarray(loads, dtype=float)
    order = np.argsort(disp)
    disp = disp[order]
    load = load[order]

    grid = np.arange(disp.min(), disp.max() + spacing / 2.0, spacing)
    interpolated = np.interp(grid, disp, load)
    return grid, interpolated


def compute_metrics(
    displacements: Iterable[float],
    loads: Iterable[float],
    service_load: float,
    smoothing_window: int = 5,
    resample_spacing: Optional[float] = None,
) -> LoadDisplacementMetrics:
    """Compute key metrics from a load–displacement curve.

    The ductility ratio is defined as the ratio between displacement at peak
    load and displacement at the service load, providing a simple measure of
    post-service deformation capacity.
    """

    disp = np.asarray(displacements, dtype=float)
    load = np.asarray(loads, dtype=float)

    order = np.argsort(disp)
    disp = disp[order]
    load = load[order]

    if resample_spacing:
        disp, load = resample_curve(disp, load, spacing=resample_spacing)

    if smoothing_window > 1:
        load = smooth_curve(load, window=smoothing_window)

    peak_idx = int(np.argmax(load))
    peak_load = float(load[peak_idx])
    displacement_at_peak = float(disp[peak_idx])

    asc_disp = disp[: peak_idx + 1]
    asc_loads = load[: peak_idx + 1]
    asc_loads = np.maximum.accumulate(asc_loads)

    displacement_at_service = float(
        np.interp(service_load, asc_loads, asc_disp, left=np.nan, right=np.nan)
    )

    secant_stiffness = float(np.nan) if displacement_at_service == 0 or np.isnan(displacement_at_service) else float(service_load / displacement_at_service)
    ductility_ratio = float(np.nan) if np.isnan(displacement_at_service) or displacement_at_service == 0 else float(displacement_at_peak / displacement_at_service)

    return LoadDisplacementMetrics(
        peak_load=peak_load,
        displacement_at_peak=displacement_at_peak,
        secant_stiffness=secant_stiffness,
        ductility_ratio=ductility_ratio,
    )


def load_curve(path: Path, displacement_column: Optional[str] = None, load_column: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Load a curve file from ``path`` returning displacement and load arrays."""

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    disp, load = _get_columns(df, displacement_column, load_column)
    return disp.to_numpy(dtype=float), load.to_numpy(dtype=float)


def _find_curve_file(run_dir: Path) -> Optional[Path]:
    """Return the first recognised curve file inside ``run_dir`` if present."""

    for extension in (".csv", ".parquet", ".pq"):
        candidate = run_dir / f"load_displacement{extension}"
        if candidate.exists():
            return candidate
    for extension in (".csv", ".parquet", ".pq"):
        matches = sorted(run_dir.glob(f"*{extension}"))
        if matches:
            return matches[0]
    return None


def summarise_runs(
    results_dir: Path,
    service_load: float,
    output_path: Path = Path("results_summary.parquet"),
    smoothing_window: int = 5,
    resample_spacing: Optional[float] = 0.001,
    displacement_column: Optional[str] = None,
    load_column: Optional[str] = None,
) -> pd.DataFrame:
    """Process all runs within ``results_dir`` and write a summary parquet file.

    Each run should live in its own subdirectory. Parameter sets are loaded
    from ``parameters.json`` when present and stored as a JSON string in the
    output to provide a stable key for grouping or comparisons.
    """

    records: List[Dict[str, object]] = []

    for run_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        curve_path = _find_curve_file(run_dir)
        if curve_path is None:
            continue

        params_path = run_dir / "parameters.json"
        parameters: Dict[str, object] = {}
        if params_path.exists():
            parameters = json.loads(params_path.read_text())

        disp, load = load_curve(curve_path, displacement_column, load_column)
        metrics = compute_metrics(
            displacements=disp,
            loads=load,
            service_load=service_load,
            smoothing_window=smoothing_window,
            resample_spacing=resample_spacing,
        )

        record = {
            "run": run_dir.name,
            "parameter_set": json.dumps(parameters, sort_keys=True),
            **asdict(metrics),
        }
        records.append(record)

    summary_df = pd.DataFrame(records)
    if not summary_df.empty:
        summary_df.to_parquet(output_path, index=False)
    return summary_df


def _build_arg_parser():
    import argparse

    parser = argparse.ArgumentParser(description="Summarise load–displacement runs.")
    parser.add_argument("results_dir", type=Path, help="Directory containing run subfolders")
    parser.add_argument("service_load", type=float, help="Service load used for secant stiffness")
    parser.add_argument("--output", type=Path, default=Path("results_summary.parquet"), help="Output Parquet path")
    parser.add_argument("--window", type=int, default=5, help="Rolling-average window for smoothing")
    parser.add_argument("--spacing", type=float, default=0.001, help="Resample spacing for displacements")
    parser.add_argument("--displacement-column", type=str, default=None, help="Custom displacement column name")
    parser.add_argument("--load-column", type=str, default=None, help="Custom load column name")
    return parser


def main(argv: Optional[List[str]] = None) -> pd.DataFrame:
    """Entry point for CLI usage."""

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    return summarise_runs(
        results_dir=args.results_dir,
        service_load=args.service_load,
        output_path=args.output,
        smoothing_window=args.window,
        resample_spacing=args.spacing,
        displacement_column=args.displacement_column,
        load_column=args.load_column,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
