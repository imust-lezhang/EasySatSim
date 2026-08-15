import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from cases.case2.experiment.evaluation.case2_metrics import (
    summarize_all_architectures,
    write_summary_csv,
)


CASE2_ROOT = PROJECT_ROOT / "cases" / "case2"
OUTPUT_DIR = CASE2_ROOT / "experiment" / "output"
FIGURE_DIR = CASE2_ROOT / "plotting" / "figures"
FIGURE_PATH = FIGURE_DIR / "fig8_network_performance.png"
SUMMARY_PATH = OUTPUT_DIR / "case2_summary_metrics.csv"


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    summary_rows = ensure_summary_rows()
    rows_by_architecture = {
        row["architecture"]: row
        for row in summary_rows
    }
    require_architectures(rows_by_architecture)

    labels = ["CL", "FL"]
    throughput = np.array([
        float(rows_by_architecture[label]["average_goodput_mbps"])
        for label in labels
    ])
    latency = np.array([
        float(rows_by_architecture[label]["final_average_latency_ms"])
        for label in labels
    ])

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    width = 0.22
    color_cl = "#D62728"
    color_fl = "#1F77B4"
    ax.yaxis.grid(True, zorder=0, linestyle="-", linewidth=0.5,
                  color="gray", alpha=0.7)
    ax.bar(1 - width / 2, throughput[0], width=width, color=color_cl,
           edgecolor="black", label="CL", lw=1.1, zorder=10, hatch="////")
    ax.bar(1 + width / 2, throughput[1], width=width, color=color_fl,
           edgecolor="black", lw=1.1, zorder=10, hatch="\\\\\\\\")
    ax.set_ylabel("Throughput (Mbps)")
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["Throughput", "Latency"])
    ax.set_xlim(0.5, 2.5)
    ax.set_ylim(0, max(throughput.max() * 1.25, 1.0))
    ax.axvline(x=1.5, color="#CDC5BF", linestyle="-", ymin=0, ymax=1,
               linewidth=1.2, zorder=8)

    ax2 = ax.twinx()
    ax2.bar(2 - width / 2, latency[0], width=width, color=color_cl,
            edgecolor="black", lw=1.1, zorder=10, hatch="////")
    ax2.bar(2 + width / 2, latency[1], width=width, color=color_fl,
            edgecolor="black", label="FL", lw=1.1, zorder=10,
            hatch="\\\\\\\\")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_ylim(0, max(latency.max() * 1.25, 1.0))

    legend = fig.legend(frameon=True, edgecolor="black", ncol=2,
                        loc="upper center", bbox_to_anchor=(0.5, 0.89))
    legend.get_frame().set_alpha(None)
    fig.savefig(FIGURE_PATH, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"Saved network performance figure to: {FIGURE_PATH}")
    return FIGURE_PATH


def ensure_summary_rows():
    rows = summarize_all_architectures()
    write_summary_csv(rows=rows, output_path=SUMMARY_PATH)
    return rows


def require_architectures(rows_by_architecture):
    missing = [
        architecture for architecture in ("CL", "FL")
        if architecture not in rows_by_architecture
    ]
    if missing:
        raise ValueError(
            "Missing architectures in case2_summary_metrics.csv: "
            + ", ".join(missing)
        )
    return


if __name__ == "__main__":
    main()
