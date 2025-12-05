"""Surrogate-driven capacity exploration.

The module builds a lightweight analytic surrogate for mat foundation
capacity and produces sweep plots, partial dependence plots, and
permutation-based feature importance using only the Python standard
library.
"""

from __future__ import annotations

import json
import math
import os
import random
import statistics
from typing import Dict, Iterable, List, Sequence, Tuple

# -----------------------------
# Surrogate model
# -----------------------------

BASELINE = {
    "width": 8.0,  # m
    "thickness": 0.5,  # m
    "su": 6000.0,  # Pa
    "rate": 0.01,  # m/s settlement rate surrogate
}


PARAM_RANGES = {
    "width": (4.0, 12.0),
    "thickness": (0.25, 1.0),
    "su": (4000.0, 9000.0),
    "rate": (0.005, 0.05),
}


def surrogate_capacity(width: float, thickness: float, su: float, rate: float) -> float:
    """Predict normalized capacity using a smooth analytic surrogate.

    The surrogate mixes classic bearing capacity trends with rate and
    thickness modifiers. It returns a capacity normalized against a
    baseline geometry (BASELINE).
    """

    # Geometry effects
    t_over_b = thickness / width
    width_factor = (width / BASELINE["width"]) ** 0.35
    thickness_factor = 1.0 + 0.55 * t_over_b - 0.25 * (t_over_b ** 2)

    # Strength and rate effects
    su_factor = su / BASELINE["su"]
    rate_ratio = max(rate, 1e-4) / BASELINE["rate"]
    rate_factor = 1.0 + 0.08 * math.log10(rate_ratio)

    # Interaction terms to make the surface non-linear
    coupling = 1.0 + 0.12 * t_over_b * math.log(width_factor + 1.1)
    micro_bulging = 1.0 + 0.04 * math.sin(2 * math.pi * t_over_b)

    return width_factor * thickness_factor * su_factor * rate_factor * coupling * micro_bulging


BASELINE_CAPACITY = surrogate_capacity(**BASELINE)


# -----------------------------
# Data helpers
# -----------------------------


def linspace(start: float, stop: float, num: int) -> List[float]:
    if num == 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + i * step for i in range(num)]


def generate_samples(n: int) -> List[Dict[str, float]]:
    samples = []
    for _ in range(n):
        samples.append(
            {
                key: random.uniform(low, high)
                for key, (low, high) in PARAM_RANGES.items()
            }
        )
    return samples


def evaluate_samples(samples: Iterable[Dict[str, float]]) -> List[float]:
    return [surrogate_capacity(**sample) / BASELINE_CAPACITY for sample in samples]


# -----------------------------
# Plotting helpers (SVG)
# -----------------------------

SVG_HEADER = """<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"""
SVG_FOOTER = "</svg>"


COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
]


def _scale(value: float, domain: Tuple[float, float], range_px: Tuple[float, float]) -> float:
    (d0, d1), (r0, r1) = domain, range_px
    if d1 == d0:
        return r0
    return r0 + (value - d0) * (r1 - r0) / (d1 - d0)


def _format_tick(value: float) -> str:
    if abs(value) >= 1:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _axes(x_range: Tuple[float, float], y_range: Tuple[float, float], w: int, h: int, margin: int) -> str:
    content = []
    x0, y0 = margin, h - margin
    x1, y1 = w - margin, margin
    # axes lines
    content.append(f"<line x1='{x0}' y1='{y0}' x2='{x1}' y2='{y0}' stroke='black' stroke-width='1' />")
    content.append(f"<line x1='{x0}' y1='{y0}' x2='{x0}' y2='{y1}' stroke='black' stroke-width='1' />")

    # ticks
    for i in range(6):
        t = x_range[0] + i * (x_range[1] - x_range[0]) / 5
        x = _scale(t, x_range, (x0, x1))
        content.append(f"<line x1='{x}' y1='{y0}' x2='{x}' y2='{y0+5}' stroke='black' stroke-width='1' />")
        content.append(f"<text x='{x}' y='{y0+18}' font-size='10' text-anchor='middle'>{_format_tick(t)}</text>")

    for i in range(6):
        t = y_range[0] + i * (y_range[1] - y_range[0]) / 5
        y = _scale(t, y_range, (y0, y1))
        content.append(f"<line x1='{x0}' y1='{y}' x2='{x0-5}' y2='{y}' stroke='black' stroke-width='1' />")
        content.append(f"<text x='{x0-8}' y='{y+3}' font-size='10' text-anchor='end'>{_format_tick(t)}</text>")
    return "\n".join(content)


def svg_line_plot(series: Sequence[Tuple[str, Sequence[float], Sequence[float]]], title: str, x_label: str, y_label: str, path: str) -> None:
    w, h, margin = 900, 420, 60
    x_min = min(min(xs) for _, xs, _ in series)
    x_max = max(max(xs) for _, xs, _ in series)
    y_min = min(min(ys) for _, _, ys in series)
    y_max = max(max(ys) for _, _, ys in series)
    y_min, y_max = min(0.9, y_min), max(1.6, y_max)

    fragments = [SVG_HEADER.format(w=w, h=h)]
    fragments.append(_axes((x_min, x_max), (y_min, y_max), w, h, margin))

    plot_w = (margin, w - margin)
    plot_h = (h - margin, margin)

    for idx, (label, xs, ys) in enumerate(series):
        pts = [
            f"{_scale(x, (x_min, x_max), plot_w):.2f},{_scale(y, (y_min, y_max), plot_h):.2f}"
            for x, y in zip(xs, ys)
        ]
        color = COLORS[idx % len(COLORS)]
        fragments.append(
            f"<polyline fill='none' stroke='{color}' stroke-width='2' points='{' '.join(pts)}' />"
        )
        lx = w - margin + 10
        ly = margin + idx * 16
        fragments.append(
            f"<rect x='{lx}' y='{ly-10}' width='12' height='12' fill='{color}' />"
        )
        fragments.append(
            f"<text x='{lx+16}' y='{ly+0}' font-size='11' alignment-baseline='middle'>{label}</text>"
        )

    fragments.append(f"<text x='{w/2}' y='{20}' font-size='14' text-anchor='middle' font-weight='bold'>{title}</text>")
    fragments.append(f"<text x='{w/2}' y='{h-10}' font-size='12' text-anchor='middle'>{x_label}</text>")
    fragments.append(
        f"<text x='{15}' y='{h/2}' font-size='12' text-anchor='middle' transform='rotate(-90 15,{h/2})'>{y_label}</text>"
    )

    fragments.append(SVG_FOOTER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(fragments))


def svg_heatmap(x_vals: Sequence[float], y_vals: Sequence[float], matrix: Sequence[Sequence[float]], title: str, x_label: str, y_label: str, path: str) -> None:
    w, h, margin = 720, 520, 70
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    plot_w = w - 2 * margin
    plot_h = h - 2 * margin
    cell_w = plot_w / len(x_vals)
    cell_h = plot_h / len(y_vals)

    flat = [v for row in matrix for v in row]
    z_min, z_max = min(flat), max(flat)

    def color(val: float) -> str:
        # simple blue-red gradient
        t = 0.0 if z_max == z_min else (val - z_min) / (z_max - z_min)
        r = int(30 + t * 200)
        g = int(60 + t * 80)
        b = int(180 - t * 150)
        return f"rgb({r},{g},{b})"

    fragments = [SVG_HEADER.format(w=w, h=h)]
    fragments.append(_axes((x_min, x_max), (y_min, y_max), w, h, margin))

    for iy, y in enumerate(y_vals):
        for ix, x in enumerate(x_vals):
            val = matrix[iy][ix]
            px = margin + ix * cell_w
            py = h - margin - (iy + 1) * cell_h
            fragments.append(
                f"<rect x='{px:.2f}' y='{py:.2f}' width='{cell_w:.2f}' height='{cell_h:.2f}' fill='{color(val)}' stroke='white' stroke-width='0.3' />"
            )

    # color bar
    bar_x = w - margin + 20
    bar_y0, bar_y1 = margin, h - margin
    fragments.append(f"<text x='{bar_x}' y='{bar_y0-10}' font-size='10'>High</text>")
    fragments.append(f"<text x='{bar_x}' y='{bar_y1+15}' font-size='10'>Low</text>")
    for i in range(50):
        t = i / 49
        val = z_min + t * (z_max - z_min)
        fragments.append(
            f"<rect x='{bar_x}' y='{bar_y0 + t*(bar_y1-bar_y0):.2f}' width='12' height='{(bar_y1-bar_y0)/50:.2f}' fill='{color(val)}' stroke='none' />"
        )

    fragments.append(f"<text x='{w/2}' y='{20}' font-size='14' text-anchor='middle' font-weight='bold'>{title}</text>")
    fragments.append(f"<text x='{w/2}' y='{h-10}' font-size='12' text-anchor='middle'>{x_label}</text>")
    fragments.append(
        f"<text x='{20}' y='{h/2}' font-size='12' text-anchor='middle' transform='rotate(-90 20,{h/2})'>{y_label}</text>"
    )

    fragments.append(SVG_FOOTER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(fragments))


# -----------------------------
# Analyses
# -----------------------------


def sweep_capacity() -> None:
    widths = linspace(4.0, 12.0, 25)
    thicknesses = [0.25, 0.5, 0.75, 1.0]
    series = []
    for t in thicknesses:
        ys = [surrogate_capacity(w, t, BASELINE["su"], BASELINE["rate"]) / BASELINE_CAPACITY for w in widths]
        series.append((f"t={t:.2f} m", widths, ys))
    svg_line_plot(series, "Normalized capacity vs. width", "Width (m)", "Normalized capacity", "outputs/normalized_capacity_vs_width.svg")

    rates = linspace(0.005, 0.05, 20)
    series = []
    for t_over_b in [0.05, 0.075, 0.1, 0.125]:
        thickness = t_over_b * BASELINE["width"]
        ys = [surrogate_capacity(BASELINE["width"], thickness, BASELINE["su"], r) / BASELINE_CAPACITY for r in rates]
        series.append((f"t/B={t_over_b:.3f}", rates, ys))
    svg_line_plot(series, "Normalized capacity vs. settlement rate", "Rate (m/s)", "Normalized capacity", "outputs/normalized_capacity_vs_rate.svg")


def partial_dependence(num_background: int = 80, grid_points: int = 30) -> None:
    background = generate_samples(num_background)
    pd_series = []

    for name, (low, high) in PARAM_RANGES.items():
        xs = linspace(low, high, grid_points)
        ys = []
        for val in xs:
            adjusted = []
            for sample in background:
                new_sample = dict(sample)
                new_sample[name] = val
                adjusted.append(new_sample)
            preds = evaluate_samples(adjusted)
            ys.append(sum(preds) / len(preds))
        pd_series.append((name, xs, ys))

    svg_line_plot(pd_series, "Partial dependence", "Parameter value", "Normalized capacity", "outputs/partial_dependence.svg")


def two_parameter_heatmap(x_name: str = "width", y_name: str = "t_over_b", grid: int = 30, fixed_su: float = 6000.0) -> None:
    x_low, x_high = PARAM_RANGES[x_name]
    x_vals = linspace(x_low, x_high, grid)

    y_low, y_high = 0.03, 0.14
    y_vals = linspace(y_low, y_high, grid)

    matrix: List[List[float]] = []
    for y in y_vals:
        row = []
        for x in x_vals:
            thickness = y * x
            cap = surrogate_capacity(x, thickness, fixed_su, BASELINE["rate"]) / BASELINE_CAPACITY
            row.append(cap)
        matrix.append(row)

    title = f"Normalized capacity heatmap: {x_name} vs t/B at su={fixed_su:.0f} Pa"
    svg_heatmap(x_vals, y_vals, matrix, title, f"{x_name} (m)", "t/B", "outputs/heatmap_width_t_over_b.svg")


def permutation_importance(n_samples: int = 200) -> Dict[str, float]:
    samples = generate_samples(n_samples)
    y_true = evaluate_samples(samples)

    def mse(a: Sequence[float], b: Sequence[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)

    base_pred = evaluate_samples(samples)
    base_error = mse(y_true, base_pred)
    reference_scale = max(base_error, statistics.pvariance(y_true), 1e-12)

    importance: Dict[str, float] = {}
    for name in PARAM_RANGES.keys():
        permuted = [dict(s) for s in samples]
        shuffled_vals = [s[name] for s in permuted]
        random.shuffle(shuffled_vals)
        for s, new_v in zip(permuted, shuffled_vals):
            s[name] = new_v
        perm_pred = evaluate_samples(permuted)
        error = mse(y_true, perm_pred)
        importance[name] = (error - base_error) / reference_scale

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/feature_importance.json", "w", encoding="utf-8") as f:
        json.dump(importance, f, indent=2)
    return importance


# -----------------------------
# Entry point
# -----------------------------


def main() -> None:
    os.makedirs("outputs", exist_ok=True)
    sweep_capacity()
    partial_dependence()
    two_parameter_heatmap()
    importance = permutation_importance()

    summary_lines = ["Permutation importance (relative MSE increase):"]
    for name, score in sorted(importance.items(), key=lambda kv: kv[1], reverse=True):
        summary_lines.append(f"- {name}: {score:.3f}")
    with open("outputs/feature_importance.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")


if __name__ == "__main__":
    main()
