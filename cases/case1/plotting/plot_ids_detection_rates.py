import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


CASE_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_OUTPUT_DIR = CASE_ROOT / "experiment" / "output"
FIGURE_OUTPUT_DIR = CASE_ROOT / "plotting" / "figures"
TEST_RESULT_PATH = EXPERIMENT_OUTPUT_DIR / "ids_test_set_metrics.csv"
CASE_RESULT_PATH = EXPERIMENT_OUTPUT_DIR / "ids_case_scenario_metrics.csv"
OUTPUT_PNG_PATH = FIGURE_OUTPUT_DIR / "fig6_detection_rates.png"
IDS_LABELS = ["S-IDS", "HR-IDS", "DL-IDS"]


def main():
    test_rows = load_test_set_results(TEST_RESULT_PATH)
    case_rows = load_case_scenario_results(CASE_RESULT_PATH)
    validate_ids(test_rows, TEST_RESULT_PATH)
    validate_ids(case_rows, CASE_RESULT_PATH)

    test_detection = np.array([
        float(test_rows[ids]["detection_rate_test_set"]) for ids in IDS_LABELS
    ])
    case_detection = np.array([
        float(case_rows[ids]["detection_rate_case_scenario"]) for ids in IDS_LABELS
    ])
    case_false_positive = np.array([
        float(case_rows[ids]["false_positive_rate_case_scenario"]) for ids in IDS_LABELS
    ])

    width = 0.2
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.yaxis.grid(True, zorder=0)

    x = np.arange(1, len(IDS_LABELS) + 1)

    ax.bar(x - width,
           test_detection,
           width=width,
           color="#FF7F24",
           edgecolor="black",
           label="Detection Rate in Test Set",
           lw=1.2,
           zorder=10,
           hatch="---")
    ax.bar(x,
           case_detection,
           width=width,
           color="#66CD00",
           edgecolor="black",
           label="Detection Rate in Case Scenario",
           lw=1.2,
           zorder=10,
           hatch="////")
    false_positive_bars = ax.bar(
        x + width,
        case_false_positive,
        width=width,
        color="#FF0000",
        edgecolor="black",
        label="False Positive Rate in Case Scenario",
        lw=1.2,
        zorder=10,
        hatch="\\\\\\\\",
    )

    ax.set_yticks([i / 10 for i in range(0, 11)])
    ax.set_yticklabels([f"{i * 10}%" for i in range(0, 11)])
    ax.set_yticks(np.arange(0, 1, 0.02), minor=True)
    ax.yaxis.grid(True, which="major", linestyle="-", linewidth=0.5, color="gray", alpha=0.7)
    ax.set_ylim(0, 1)
    ax.set_xticks(x)
    ax.set_xticklabels(IDS_LABELS)
    ax.set_xlim(0.5, len(IDS_LABELS) + 0.5)
    ax.set_ylabel("Percentage")
    legend = ax.legend(frameon=True, edgecolor="black", labelspacing=0.1, ncol=1, loc="upper left")
    legend.get_frame().set_alpha(None)

    add_false_positive_labels(
        ax=ax,
        bars=false_positive_bars,
        values=case_false_positive,
    )

    OUTPUT_PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG_PATH, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"Saved: {OUTPUT_PNG_PATH}")
    return


def add_false_positive_labels(ax, bars, values):
    for index, (bar, value) in enumerate(zip(bars, values)):
        percentage = float(value) * 100.0
        label = "0%" if np.isclose(percentage, 0.0) else f"{percentage:.2f}%"
        label_y = max(float(value) + 0.012, 0.035)
        label_x = bar.get_x() + bar.get_width() / 2.0
        if index == len(bars) - 1:
            label_x -= 0.04
        ax.text(
            label_x,
            label_y,
            label,
            color="#FF0000",
            fontweight="bold",
            ha="left",
            va="bottom",
            zorder=12,
        )
    return


def load_test_set_results(path):
    return load_detection_results(
        path,
        required_columns=[
            "ids",
            "detection_rate_test_set",
        ],
        missing_message=(
            f"Test-set IDS metrics file was not found: {path}. "
            "Run: python -m cases.case1.experiment.evaluation.evaluate_test_dataset"
        ),
    )


def load_case_scenario_results(path):
    return load_detection_results(
        path,
        required_columns=[
            "ids",
            "detection_rate_case_scenario",
            "false_positive_rate_case_scenario",
        ],
        missing_message=(
            f"Case-scenario IDS metrics file was not found: {path}. "
            "These values must be generated from a completed satellite-network "
            "simulation log, not from the static payload test set. Expected "
            "columns: ids,detection_rate_case_scenario,"
            "false_positive_rate_case_scenario."
        ),
    )


def load_detection_results(path, required_columns, missing_message):
    if not path.exists():
        raise FileNotFoundError(missing_message)
    with path.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"Detection result file is empty: {path}")
    missing_columns = [
        column for column in required_columns
        if column not in rows[0]
    ]
    if missing_columns:
        raise ValueError(
            f"Detection result file has missing columns: {path}; "
            f"missing={missing_columns}"
        )
    return {row["ids"]: row for row in rows}


def validate_ids(rows, path):
    missing_ids = [ids for ids in IDS_LABELS if ids not in rows]
    if missing_ids:
        raise ValueError(
            f"Detection result file does not contain all IDS rows: {path}; "
            f"missing={missing_ids}"
        )
    return


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as error:
        print(f"Plotting skipped: {error}")
        raise SystemExit(1)
