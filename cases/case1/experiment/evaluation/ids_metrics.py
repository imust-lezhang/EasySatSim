from cases.case1.experiment.data.test_dataset import TEST_DATASET_PROFILE
from cases.case1.experiment.data.test_dataset import test_benign_payloads
from cases.case1.experiment.data.test_dataset import test_malicious_payloads


def evaluate_test_dataset(detect_func):
    true_positive = count_detected(detect_func, test_malicious_payloads)
    false_negative = len(test_malicious_payloads) - true_positive
    false_positive = count_detected(detect_func, test_benign_payloads)
    true_negative = len(test_benign_payloads) - false_positive
    total = true_positive + false_negative + false_positive + true_negative

    metrics = {
        "tp": true_positive,
        "fn": false_negative,
        "fp": false_positive,
        "tn": true_negative,
        "accuracy": safe_rate(true_positive + true_negative, total),
        "detection_rate_test_set": safe_rate(true_positive, len(test_malicious_payloads)),
        "false_positive_rate_test_set": safe_rate(false_positive, len(test_benign_payloads)),
        "test_malicious_total": len(test_malicious_payloads),
        "test_benign_total": len(test_benign_payloads),
        "test_dataset_profile": TEST_DATASET_PROFILE,
    }
    return metrics


def count_detected(detect_func, payloads):
    detected_count = 0
    for payload in payloads:
        if bool(detect_func(payload)):
            detected_count += 1
    return detected_count


def safe_rate(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


def print_test_metrics(title, metrics):
    test_profile = metrics["test_dataset_profile"]
    print(title)
    print(
        f"Test dataset: {test_profile['malicious']} malicious, "
        f"{test_profile['benign']} benign, {test_profile['total']} total"
    )
    print(
        f"Confusion matrix: TP={metrics['tp']}, FN={metrics['fn']}, "
        f"FP={metrics['fp']}, TN={metrics['tn']}"
    )
    print(
        f"Accuracy in Test Set: {metrics['accuracy']:.2%}"
    )
    print(
        f"Detection Rate in Test Set: "
        f"{metrics['tp']}/{metrics['test_malicious_total']} "
        f"= {metrics['detection_rate_test_set']:.2%}"
    )
    print(
        f"False Positive Rate in Test Set: "
        f"{metrics['fp']}/{metrics['test_benign_total']} "
        f"= {metrics['false_positive_rate_test_set']:.2%}"
    )
    return
