import csv
from pathlib import Path

from cases.case1.experiment.ids import ids_deep_learning
from cases.case1.experiment.ids import ids_heuristic
from cases.case1.experiment.ids import ids_signature
from cases.case1.experiment.evaluation.ids_metrics import evaluate_test_dataset


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = EXPERIMENT_ROOT / "output" / "ids_test_set_metrics.csv"


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    dl_model = ids_deep_learning.get_runtime_model()
    results = [
        ("S-IDS", evaluate_test_dataset(lambda payload: ids_signature.detect(payload)[0])),
        ("HR-IDS", evaluate_test_dataset(lambda payload: ids_heuristic.detect(payload)[0])),
        ("DL-IDS", evaluate_test_dataset(lambda payload: ids_deep_learning.detect(payload, dl_model)[0])),
    ]

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "ids",
            "tp",
            "fp",
            "tn",
            "fn",
            "accuracy_test_set",
            "detection_rate_test_set",
            "false_positive_rate_test_set",
            "test_malicious_total",
            "test_benign_total",
        ])
        for ids_name, metrics in results:
            writer.writerow([
                ids_name,
                metrics["tp"],
                metrics["fp"],
                metrics["tn"],
                metrics["fn"],
                metrics["accuracy"],
                metrics["detection_rate_test_set"],
                metrics["false_positive_rate_test_set"],
                metrics["test_malicious_total"],
                metrics["test_benign_total"],
            ])

    print(f"IDS test-set metrics saved to: {OUTPUT_PATH}")
    for ids_name, metrics in results:
        print(
            f"{ids_name}: accuracy_test={metrics['accuracy']:.2%}, "
            f"detection_test={metrics['detection_rate_test_set']:.2%}, "
            f"fpr_test={metrics['false_positive_rate_test_set']:.2%}"
        )
    return OUTPUT_PATH


if __name__ == "__main__":
    main()
