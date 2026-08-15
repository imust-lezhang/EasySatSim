import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from cases.case2.experiment.evaluation.case2_metrics import (
    DEFAULT_WARMUP_SECONDS,
    summarize_all_architectures,
    write_summary_csv,
)


def main():
    parser = argparse.ArgumentParser(
        description="Summarize Case 2 CL/FL learning and network metrics."
    )
    parser.add_argument(
        "--warmup-seconds",
        type=float,
        default=DEFAULT_WARMUP_SECONDS,
        help="Ignore early initialization seconds for window-average metrics.",
    )
    args = parser.parse_args()

    rows = summarize_all_architectures(warmup_seconds=args.warmup_seconds)
    output_path = write_summary_csv(rows=rows)
    print(f"Case 2 summary metrics saved to: {output_path}")
    for row in rows:
        print(
            f"{row['architecture']}: "
            f"rounds={row['learning_rounds']}, "
            f"final_acc={format_optional_percent(row['final_test_accuracy_percent'])}, "
            f"best_acc={format_optional_percent(row['best_test_accuracy_percent'])}, "
            f"goodput={row['average_goodput_mbps']:.3f} Mbps, "
            f"latency={row['final_average_latency_ms']:.3f} ms, "
            f"packet_loss={row['packet_loss_rate']:.2%}"
        )
    return output_path


def format_optional_percent(value):
    if value == "":
        return "N/A"
    return f"{float(value):.2f}%"


if __name__ == "__main__":
    main()
