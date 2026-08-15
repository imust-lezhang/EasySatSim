import csv
from pathlib import Path

from cases.case1.experiment.evaluation.ids_metrics import safe_rate
from cases.case1.experiment.integration.ids_event_log import GROUND_TRUTH_BENIGN
from cases.case1.experiment.integration.ids_event_log import GROUND_TRUTH_MALICIOUS
from cases.case1.experiment.integration.ids_event_log import text_to_bool


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = EXPERIMENT_ROOT / "output"
EVENT_LOG_PATTERN = "ids_events_*.csv"
OUTPUT_PATH = OUTPUT_DIR / "ids_case_scenario_metrics.csv"


def main():
    event_paths = sorted(OUTPUT_DIR.glob(EVENT_LOG_PATTERN))
    if not event_paths:
        raise FileNotFoundError(
            f"No IDS event logs found under {OUTPUT_DIR}. "
            "Run the satellite-network case scenario first."
        )

    summaries = {}
    for event_path in event_paths:
        update_summaries_from_event_log(summaries=summaries, event_path=event_path)

    write_case_scenario_metrics(summaries=summaries, output_path=OUTPUT_PATH)
    print(f"IDS case-scenario metrics saved to: {OUTPUT_PATH}")
    for row in build_metric_rows(summaries):
        print(
            f"{row['ids']}: case_detection={float(row['detection_rate_case_scenario']):.2%}, "
            f"case_fpr={float(row['false_positive_rate_case_scenario']):.2%}, "
            f"malicious={row['case_malicious_total']}, benign={row['case_benign_total']}"
        )
    return OUTPUT_PATH


def update_summaries_from_event_log(summaries, event_path):
    with event_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            ids_label = row["ids"]
            summary = summaries.setdefault(ids_label, new_summary(ids_label=ids_label))
            summary["event_file_count"].add(str(event_path))
            update_summary(summary=summary, row=row)
    return


def new_summary(ids_label):
    return {
        "ids": ids_label,
        "true_positive": 0,
        "false_negative": 0,
        "false_positive": 0,
        "true_negative": 0,
        "total_events": 0,
        "event_file_count": set(),
    }


def update_summary(summary, row):
    ground_truth = row["ground_truth"]
    detected = text_to_bool(row["detected"])
    summary["total_events"] += 1

    if ground_truth == GROUND_TRUTH_MALICIOUS:
        if detected:
            summary["true_positive"] += 1
        else:
            summary["false_negative"] += 1
        return

    if ground_truth == GROUND_TRUTH_BENIGN:
        if detected:
            summary["false_positive"] += 1
        else:
            summary["true_negative"] += 1
        return

    raise ValueError(f"Unsupported ground_truth value: {ground_truth}")


def write_case_scenario_metrics(summaries, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_metric_rows(summaries)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return


def build_metric_rows(summaries):
    rows = []
    for ids_label in sorted(summaries):
        summary = summaries[ids_label]
        true_positive = summary["true_positive"]
        false_negative = summary["false_negative"]
        false_positive = summary["false_positive"]
        true_negative = summary["true_negative"]
        malicious_total = true_positive + false_negative
        benign_total = false_positive + true_negative
        rows.append({
            "ids": ids_label,
            "case_detected": true_positive,
            "case_malicious_total": malicious_total,
            "detection_rate_case_scenario": safe_rate(true_positive, malicious_total),
            "case_false_positive": false_positive,
            "case_benign_total": benign_total,
            "false_positive_rate_case_scenario": safe_rate(false_positive, benign_total),
            "true_positive": true_positive,
            "false_negative": false_negative,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "total_events": summary["total_events"],
            "event_file_count": len(summary["event_file_count"]),
        })
    if not rows:
        raise ValueError("No IDS events were found in the event logs.")
    return rows


if __name__ == "__main__":
    main()
