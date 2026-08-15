from cases.case1.experiment.ids import ids_deep_learning
from cases.case1.experiment.evaluation.ids_metrics import evaluate_test_dataset
from cases.case1.experiment.evaluation.ids_metrics import print_test_metrics


def main():
    model = ids_deep_learning.train_and_save_model()
    metrics = evaluate_test_dataset(lambda payload: ids_deep_learning.detect(payload, model)[0])
    print(f"DL IDS model saved to: {ids_deep_learning.DEFAULT_MODEL_PATH}")
    print_test_metrics("Deep learning IDS saved-model evaluation", metrics)
    return ids_deep_learning.DEFAULT_MODEL_PATH


if __name__ == "__main__":
    main()
