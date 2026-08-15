from cases.case1.experiment.data.malicious_code_library import malicious_code_library
from cases.case1.experiment.data.normal_payload_library import normal_payload_library


TEST_BENIGN_SAMPLE_COUNT = 40


test_malicious_payloads = list(malicious_code_library)
test_benign_payloads = list(normal_payload_library[:TEST_BENIGN_SAMPLE_COUNT])


TEST_DATASET_PROFILE = {
    "malicious": len(test_malicious_payloads),
    "benign": len(test_benign_payloads),
    "total": len(test_malicious_payloads) + len(test_benign_payloads),
}
