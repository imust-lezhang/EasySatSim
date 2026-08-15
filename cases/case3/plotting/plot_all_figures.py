from cases.case3.plotting._common import load_plot_inputs, result_counts
from cases.case3.plotting.plot_average_hop_count import plot_average_hop_count
from cases.case3.plotting.plot_undelivered_ratio import plot_undelivered_ratio


def main():
    frame, metadata = load_plot_inputs()
    undelivered_path = plot_undelivered_ratio(frame, metadata)
    hop_path = plot_average_hop_count(frame, metadata)
    run_count, seed_count = result_counts(frame)
    print(
        f"[Case 3 plotting] Created 2 figures from {run_count} runs "
        f"({seed_count} seeds per routing curve)."
    )
    print(f"Saved undelivered-ratio figure to: {undelivered_path}")
    print(f"Saved average-hop-count figure to: {hop_path}")


if __name__ == "__main__":
    main()
