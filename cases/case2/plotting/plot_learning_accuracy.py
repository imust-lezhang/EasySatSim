import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))


CASE2_ROOT = PROJECT_ROOT / "cases" / "case2"
OUTPUT_DIR = CASE2_ROOT / "experiment" / "output"
FIGURE_DIR = CASE2_ROOT / "plotting" / "figures"
FIGURE_PATH = FIGURE_DIR / "fig8_accuracy.png"


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cl_points = read_accuracy_points(
        path=OUTPUT_DIR / "cl_learning_metrics.csv",
    )
    fl_points = read_accuracy_points(
        path=OUTPUT_DIR / "fl_learning_metrics.csv",
    )
    require_points(cl_points=cl_points, fl_points=fl_points)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.yaxis.grid(True, zorder=0, linestyle="-", linewidth=0.5,
                  color="gray", alpha=0.7)
    plot_curve(ax=ax, points=cl_points, label="CL", color="#D62728",
               marker="o")
    plot_curve(ax=ax, points=fl_points, label="FL", color="#1F77B4",
               marker="v")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Test Accuracy")
    ax.set_xlim(0, max(get_max_time(cl_points, fl_points), 1000.0))
    ax.set_ylim(0, 1)
    ax.set_yticks([index * 0.1 for index in range(0, 11)])
    ax.set_yticklabels([f"{index * 10}%" for index in range(0, 11)])
    legend = ax.legend(frameon=True, edgecolor="black", loc="lower right")
    legend.get_frame().set_alpha(None)
    fig.savefig(FIGURE_PATH, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"Saved learning accuracy figure to: {FIGURE_PATH}")
    return FIGURE_PATH


def read_accuracy_points(path):
    if not path.exists():
        return []
    points = [(0.0, 0.0)]
    has_metric_row = False
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            time_value = float(row.get("Simulation_Time", 0.0))
            accuracy = float(row.get("Test_Accuracy", 0.0)) / 100.0
            points.append((time_value, accuracy))
            has_metric_row = True
    if not has_metric_row:
        return []
    return points


def require_points(cl_points, fl_points):
    missing = []
    if not cl_points:
        missing.append("cl_learning_metrics.csv")
    if not fl_points:
        missing.append("fl_learning_metrics.csv")
    if missing:
        raise FileNotFoundError(
            "Missing learning metric files: "
            + ", ".join(missing)
            + "\nRun CL and FL first, then run:\n"
            "python -m cases.case2.experiment.evaluation.summarize_case2_results"
        )
    return


def get_max_time(*point_sets):
    max_time = 0.0
    for points in point_sets:
        for time_value, _ in points:
            max_time = max(max_time, time_value)
    return max_time


def plot_curve(ax, points, label, color, marker):
    times = [point[0] for point in points]
    accuracies = [point[1] for point in points]
    ax.plot(
        times,
        accuracies,
        linewidth=0.9,
        markersize=3,
        markeredgewidth=0.5,
        zorder=10,
        color=color,
        markerfacecolor="white",
        marker=marker,
        label=label,
    )
    return


if __name__ == "__main__":
    main()
