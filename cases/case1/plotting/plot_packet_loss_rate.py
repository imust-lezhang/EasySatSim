import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

CASE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CASE_ROOT.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.config_loader import load_configuration


cg = load_configuration("cases/case1/src")

EXPERIMENT_OUTPUT_DIR = CASE_ROOT / "experiment" / "output"
FIGURE_OUTPUT_DIR = CASE_ROOT / "plotting" / "figures"
OUTPUT_PNG_PATH = FIGURE_OUTPUT_DIR / "fig6_packet_loss_rate.png"
PLOT_WARMUP_SECONDS = 10

IDS_SERIES = [
    {
        "mode": "signature",
        "label": "S-IDS",
        "color": "#FF0000",
        "marker": "o",
        "markersize": 2.5,
        "patterns": [
            "easysatsim_result_signature_*.csv",
            "signature.csv",
        ],
    },
    {
        "mode": "heuristic",
        "label": "HR-IDS",
        "color": "#4876FF",
        "marker": "v",
        "markersize": 2.5,
        "patterns": [
            "easysatsim_result_heuristic_*.csv",
            "heuristic.csv",
        ],
    },
    {
        "mode": "dl",
        "label": "DL-IDS",
        "color": "#76EE00",
        "marker": "*",
        "markersize": 3.5,
        "patterns": [
            "easysatsim_result_dl_*.csv",
            "easysatsim_result_deep_learning_*.csv",
            "dl.csv",
            "real_deep.csv",
            "deep_learning.csv",
        ],
    },
]

REQUIRED_COLUMNS = [
    "Time",
    "Current_Arrived_Packets_Number",
    "Current_Lost_Packets_Number",
]


def main():
    series_data = []
    for series in IDS_SERIES:
        result_path = find_network_result_path(series)
        time_values, loss_rate = load_packet_loss_rate(result_path)
        series_data.append((series, result_path, time_values, loss_rate))

    plot_packet_loss_rate(series_data)
    return


def find_network_result_path(series):
    candidates = []
    for pattern in series["patterns"]:
        candidates.extend(EXPERIMENT_OUTPUT_DIR.glob(pattern))
    candidates = [
        path for path in candidates
        if path.is_file()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"Cannot find network result CSV for {series['label']} under {EXPERIMENT_OUTPUT_DIR}. "
            f"Expected one of: {series['patterns']}. "
            "Run cases/case1/main.py once for each IDS mode after the output-prefix update."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_packet_loss_rate(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"Network result CSV is empty: {path}")

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in rows[0]
    ]
    if missing_columns:
        raise ValueError(
            f"Network result CSV has missing columns: {path}; "
            f"missing={missing_columns}"
        )

    time_values = np.array([float(row["Time"]) for row in rows], dtype=float)
    arrived_packets = np.array([
        float(row["Current_Arrived_Packets_Number"]) for row in rows
    ], dtype=float)
    lost_packets = np.array([
        float(row["Current_Lost_Packets_Number"]) for row in rows
    ], dtype=float)

    completed_packets = arrived_packets + lost_packets
    loss_rate = np.divide(
        lost_packets,
        completed_packets,
        out=np.zeros_like(lost_packets, dtype=float),
        where=completed_packets > 0,
    )
    stable_mask = time_values >= PLOT_WARMUP_SECONDS
    time_values = time_values[stable_mask]
    loss_rate = loss_rate[stable_mask]
    return time_values, loss_rate


def plot_packet_loss_rate(series_data):
    output_paths = [path for _, path, _, _ in series_data]
    print("Packet-loss plot input files:")
    for path in output_paths:
        print(f"  {path}")
    print(f"Warm-up samples skipped: Time < {PLOT_WARMUP_SECONDS}s")

    max_time = max(float(np.max(time_values)) for _, _, time_values, _ in series_data)
    max_rate = max(float(np.max(loss_rate)) for _, _, _, loss_rate in series_data)
    y_upper = max(0.8, min(1.0, max_rate * 1.15 if max_rate > 0 else 0.8))

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.yaxis.grid(True, zorder=0)

    add_observation_windows(ax=ax, y_upper=y_upper, max_time=max_time)

    for series, path, time_values, loss_rate in series_data:
        print_series_summary(series=series,
                             path=path,
                             time_values=time_values,
                             loss_rate=loss_rate)
        ax.plot(time_values,
                loss_rate,
                linewidth=0.8,
                markersize=series["markersize"],
                markeredgewidth=0.4,
                zorder=10,
                color=series["color"],
                markerfacecolor="white",
                marker=series["marker"],
                label=series["label"])

    ax.set_yticks(np.arange(0, 1.01, 0.02), minor=True)
    ax.yaxis.grid(True, which="major", linestyle="-", linewidth=0.5, color="gray", alpha=0.7)
    ax.yaxis.grid(True, which="minor", linestyle=":", linewidth=0.5, color="gray", alpha=0.7)
    ax.set_yticks([i / 10 for i in range(0, 11)])
    ax.set_yticklabels([f"{i * 10}%" for i in range(0, 11)])
    ax.set_xlim(0, max(getattr(cg, "CASE_SIMULATION_END_TIME", 800), max_time))
    ax.set_ylim(0, y_upper)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Packet Loss Rate")

    legend = ax.legend(frameon=True,
                       edgecolor="black",
                       labelspacing=0.1,
                       ncol=3,
                       loc="upper right")
    legend.get_frame().set_alpha(None)

    OUTPUT_PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG_PATH, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"Saved: {OUTPUT_PNG_PATH}")
    return


def add_observation_windows(ax, y_upper, max_time):
    attack_start = getattr(cg, "CASE_ATTACK_START_TIME", 100)
    attack_end = getattr(cg, "CASE_ATTACK_END_TIME", 500)
    simulation_end = min(getattr(cg, "CASE_SIMULATION_END_TIME", 800), max_time)
    recovery_start = min(attack_end + 100, simulation_end)

    add_shaded_window(ax=ax,
                      start=attack_start,
                      end=attack_end,
                      y_upper=y_upper,
                      color="#CDC5BF",
                      label="Attack Events")
    if recovery_start < simulation_end:
        add_shaded_window(ax=ax,
                          start=recovery_start,
                          end=simulation_end,
                          y_upper=y_upper,
                          color="#CDC5BF",
                          label="Stable\nOperation")
    return


def add_shaded_window(ax, start, end, y_upper, color, label):
    if end <= start:
        return
    window_height = y_upper * 0.81
    ax.vlines(
        [start, end],
        ymin=0,
        ymax=window_height,
        color=color,
        linestyle="-",
        linewidth=1.2,
        zorder=8,
    )
    rect = Rectangle((start, 0),
                     end - start,
                     window_height,
                     color=color,
                     alpha=0.3,
                     zorder=8)
    ax.add_patch(rect)
    ax.text(
        (start + end) / 2.0,
        window_height * 0.96,
        label,
        color="black",
        fontweight="bold",
        ha="center",
        va="top",
        linespacing=1.05,
        zorder=12,
    )
    return


def print_series_summary(series, path, time_values, loss_rate):
    attack_start = getattr(cg, "CASE_ATTACK_START_TIME", 100)
    attack_end = getattr(cg, "CASE_ATTACK_END_TIME", 500)
    recovery_start = attack_end + 100

    attack_mask = (time_values >= attack_start) & (time_values <= attack_end)
    recovery_mask = time_values >= recovery_start
    attack_mean = safe_mean(loss_rate[attack_mask])
    recovery_mean = safe_mean(loss_rate[recovery_mask])
    overall_mean = safe_mean(loss_rate)
    print(
        f"{series['label']}: file={path.name}, "
        f"overall={overall_mean:.2%}, "
        f"attack={attack_mean:.2%}, "
        f"post_attack={recovery_mean:.2%}"
    )
    return


def safe_mean(values):
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as error:
        print(f"Plotting skipped: {error}")
        raise SystemExit(1)
