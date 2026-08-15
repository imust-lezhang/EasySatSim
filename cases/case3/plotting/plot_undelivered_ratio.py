import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cases.case3.plotting._common import (
    FIGURE_DIR,
    draw_series,
    draw_timeline,
    finish_axis,
    load_plot_inputs,
    result_counts,
)


FIGURE_PATH = FIGURE_DIR / "CASE3_UNDELIVERED_RATIO.png"


def plot_undelivered_ratio(frame, metadata, path=FIGURE_PATH):
    plot_frame = frame.copy()
    plot_frame["undelivered_ratio"] = 1.0 - plot_frame["delivery_ratio"]

    fig, axis = plt.subplots(figsize=(6, 5))
    draw_timeline(axis, metadata)
    draw_series(
        axis,
        plot_frame,
        "undelivered_ratio",
        lower_bound=0.0,
        upper_bound=1.0,
    )
    y_max = _rounded_percentage_ceiling(plot_frame)
    axis.set_ylim(0.0, y_max)
    axis.set_ylabel("Undelivered Ratio")
    major_ticks = np.arange(0.0, y_max + 0.001, 0.1)
    axis.set_yticks(major_ticks)
    axis.set_yticklabels([f"{value * 100:.0f}%" for value in major_ticks])
    axis.set_yticks(np.arange(0.0, y_max + 0.001, 0.02), minor=True)
    finish_axis(axis)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=400)
    plt.close(fig)
    return path


def _rounded_percentage_ceiling(frame):
    maximum_mean = (
        frame.groupby(["mode", "bin_center"])["undelivered_ratio"].mean().max()
    )
    if not np.isfinite(maximum_mean):
        raise ValueError("No finite undelivered-ratio values are available to plot.")
    return max(0.1, math.ceil(maximum_mean * 10.0 - 1e-12) / 10.0)


def main():
    frame, metadata = load_plot_inputs()
    path = plot_undelivered_ratio(frame, metadata)
    run_count, seed_count = result_counts(frame)
    print(
        f"[Case 3 plotting] Undelivered-ratio figure aggregated {run_count} runs "
        f"({seed_count} seeds per routing curve)."
    )
    print(f"Saved undelivered-ratio figure to: {path}")


if __name__ == "__main__":
    main()
