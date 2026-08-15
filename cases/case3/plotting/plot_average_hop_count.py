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


FIGURE_PATH = FIGURE_DIR / "CASE3_AVERAGE_HOP_COUNT.png"


def plot_average_hop_count(frame, metadata, path=FIGURE_PATH):
    fig, axis = plt.subplots(figsize=(6, 5))
    draw_timeline(axis, metadata)
    draw_series(axis, frame, "average_hop_count", lower_bound=0.0)
    y_min = 4
    y_max = 10
    axis.set_ylim(y_min, y_max)
    even_ticks = np.arange(y_min, y_max + 1, 2)
    odd_ticks = np.arange(y_min + 1, y_max + 1, 2)
    axis.set_yticks(even_ticks)
    axis.set_yticks(odd_ticks, minor=True)
    axis.set_yticklabels([str(value) for value in even_ticks])
    axis.set_yticklabels([str(value) for value in odd_ticks], minor=True)
    axis.tick_params(axis="y", which="minor", labelsize=10)
    axis.set_ylabel("Average Hop Count")
    finish_axis(axis)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=400)
    plt.close(fig)
    return path


def main():
    frame, metadata = load_plot_inputs()
    path = plot_average_hop_count(frame, metadata)
    run_count, seed_count = result_counts(frame)
    print(
        f"[Case 3 plotting] Average-hop figure aggregated {run_count} runs "
        f"({seed_count} seeds per routing curve)."
    )
    print(f"Saved average-hop-count figure to: {path}")


if __name__ == "__main__":
    main()
