import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from cases.case2.experiment.evaluation.summarize_case2_results import (
    main as summarize_results,
)
from cases.case2.plotting.plot_learning_accuracy import (
    main as plot_learning_accuracy,
)
from cases.case2.plotting.plot_network_performance import (
    main as plot_network_performance,
)


def main():
    summarize_results()
    plot_learning_accuracy()
    plot_network_performance()
    return


if __name__ == "__main__":
    main()
