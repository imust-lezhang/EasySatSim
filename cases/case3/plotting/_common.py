import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


CASE3_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = CASE3_ROOT / "experiment" / "output"
FIGURE_DIR = CASE3_ROOT / "plotting" / "figures"
TIME_BIN_PATH = OUTPUT_DIR / "CASE3_TIME_BIN_METRICS.csv"
MANIFEST_PATH = OUTPUT_DIR / "CASE3_RUN_MANIFEST.csv"
MODES = ("centralized", "distributed")
COLORS = {"centralized": "#D62728", "distributed": "#1F77B4"}
STYLES = {
    "centralized": ("Centralized Routing", "o"),
    "distributed": ("Distributed Routing", "v"),
}


def load_plot_inputs():
    if not TIME_BIN_PATH.is_file() or not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            "Processed metrics are missing. Run "
            "`python -m cases.case3.experiment.evaluation.process_results` first."
        )
    manifest = pd.read_csv(MANIFEST_PATH)
    metadata_path = Path(str(manifest.iloc[0]["metadata_path"]))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    frame = pd.read_csv(TIME_BIN_PATH)
    seeds = sorted(manifest["seed"].astype(int).unique())
    print(f"[Case 3 plotting] Metrics file: {TIME_BIN_PATH}")
    print(f"[Case 3 plotting] Run manifest: {MANIFEST_PATH}")
    print(
        f"[Case 3 plotting] Included runs: {len(manifest)} "
        f"({len(seeds)} seeds x {manifest['mode'].nunique()} modes)"
    )
    print(f"[Case 3 plotting] Seeds: {', '.join(map(str, seeds))}")
    print("[Case 3 plotting] Source event files:")
    for index, row in manifest.iterrows():
        print(
            f"  {index + 1:02d}. mode={row['mode']}, seed={int(row['seed'])}: "
            f"{row['event_log_path']}"
        )
    return frame, metadata


def result_counts(frame):
    runs = frame[["mode", "seed"]].drop_duplicates()
    return len(runs), runs["seed"].nunique()


def timeline(metadata):
    failure = float(metadata["failure_time"])
    interval = float(metadata["centralized_route_refresh_interval"])
    refresh = math.ceil((failure + 1e-12) / interval) * interval
    return float(metadata["running_time"]), failure, refresh


def draw_timeline(axis, metadata):
    duration, failure, refresh = timeline(metadata)
    axis.axvspan(failure, duration, color="#CDC5BF", alpha=0.22, zorder=0)
    for boundary in (failure, refresh):
        if 0.0 < boundary < duration:
            axis.axvline(
                boundary,
                color="#666666",
                linestyle="--",
                linewidth=1.0,
                zorder=8,
            )
    failed_satellite_id = int(metadata["failed_satellite_id"])
    phase_labels = [
        (0.0, failure, "Normal Operation"),
        (failure, refresh, "Failure Before\nRefresh"),
        (refresh, duration, "Failure After\nRefresh"),
    ]
    for start, end, label in phase_labels:
        if end <= start:
            continue
        label_x = (start + end) / 2.0
        if start == failure:
            label_x -= min(2.5, (end - start) * 0.05)
        elif start == refresh:
            label_x += min(5.0, (end - start) * 0.1)
        axis.text(
            label_x,
            0.99,
            label,
            transform=axis.get_xaxis_transform(),
            color="black",
            fontweight="bold",
            fontsize=8,
            ha="center",
            va="top",
            linespacing=1.05,
            zorder=12,
        )
    event_labels = [
        (failure, f"Satellite {failed_satellite_id} Failure ({failure:g} s)"),
        (refresh, f"Centralized Route Refresh ({refresh:g} s)"),
    ]
    for event_time, label in event_labels:
        if not 0.0 < event_time < duration:
            continue
        axis.text(
            event_time - 2.0,
            0.04,
            label,
            transform=axis.get_xaxis_transform(),
            color="#666666",
            fontsize=6.5,
            fontweight="normal",
            rotation=90,
            rotation_mode="anchor",
            ha="left",
            va="bottom",
            zorder=12,
        )
    axis.set_xlim(0.0, duration)


def draw_series(axis, frame, metric, lower_bound=None, upper_bound=None):
    for mode in MODES:
        grouped = frame[frame["mode"] == mode].groupby("bin_center")[metric]
        mean = grouped.mean()
        std = grouped.std(ddof=1).fillna(0.0)
        x = mean.index.to_numpy(dtype=float)
        y = mean.to_numpy(dtype=float)
        spread = std.to_numpy(dtype=float)
        low = y - spread
        high = y + spread
        if lower_bound is not None:
            low = np.clip(low, lower_bound, None)
        if upper_bound is not None:
            high = np.clip(high, None, upper_bound)
        if np.any(spread > 0):
            axis.fill_between(x, low, high, color=COLORS[mode], alpha=0.12, linewidth=0)
        label, marker = STYLES[mode]
        axis.plot(
            x,
            y,
            color=COLORS[mode],
            marker=marker,
            markerfacecolor="white",
            markeredgewidth=0.5,
            markersize=3.0,
            linewidth=0.9,
            label=label,
            zorder=10,
        )


def finish_axis(axis):
    axis.yaxis.grid(True, which="major", color="gray", linewidth=0.5, alpha=0.7)
    axis.yaxis.grid(True, which="minor", color="gray", linestyle=":", linewidth=0.5, alpha=0.7)
    legend = axis.legend(frameon=True, edgecolor="black", labelspacing=0.1, loc="best")
    legend.get_frame().set_alpha(None)
    axis.set_xlabel("Time (seconds)")
    axis.tick_params(axis="both", which="both", direction="out")
