# Case 1 Tutorial: Adding an Intrusion Detection Scenario

This tutorial explains how Case 1 is built on EasySatSim. It is intended for readers who want to understand **how to add a complete research case**, rather than only how to run the finished scripts.

The tutorial follows the actual implementation order of the case. Each step introduces only a small set of files, explains their roles, and provides a simple verification method before moving to the next step.

## Prerequisites

Run all commands from the EasySatSim project root. Install the complete Case 1 environment with:

```powershell
python -m pip install -r cases/case1/requirements.txt
```

This requirements file installs the dependencies required by the EasySatSim core simulation, pandas and Matplotlib for result evaluation and plotting, and TensorFlow for the deep learning IDS. The pinned versions are the versions verified for the current repository.

## 1. Tutorial Goal

The goal of this case is to add an intrusion detection experiment to EasySatSim **without rewriting the EasySatSim core code**.

The final scenario includes:

- a LEO satellite network with fixed user locations;
- a group of malicious users that send attack payloads to satellite application port `22`;
- a small amount of benign traffic sent to port `22` for measuring false positives;
- three intrusion detection methods:
  - signature based IDS;
  - heuristic rule based IDS;
  - deep learning based IDS;
- a satellite side IDS engine that loads one IDS mode for each run and inspects the port `22` payloads received by satellites;
- IDS event logs that record whether each port `22` payload is malicious or benign and whether it is detected;
- evaluation programs that calculate detection rate and false positive rate;
- plotting programs that generate the two PNG figures used in the paper.

This organization makes the EasySatSim extension points clear. Users only need to add case specific behaviors, protocol stack logic, data, IDS methods, and analysis programs around the existing EasySatSim framework, without modifying the simulator core mechanisms.

### How to Use This Tutorial

This document supports two reading paths:

- If you want to reproduce the completed experiment, first install the prerequisites and then follow Sections 19 through 21 directly. Read the corresponding implementation steps later when you need to understand or modify a component.
- If you want to understand how to add a new case to EasySatSim, follow Sections 3 through 18 in order. Each step identifies the corresponding extension point, shows the key implementation logic, and provides a verification command.

The code blocks in the implementation steps mainly show key excerpts to explain the design. They do not repeat every import, validation branch, or helper function in the repository. The source files identified in each step and in the following table are the complete executable implementations.

### EasySatSim Extension Map

| Layer | Case 1 addition | Complete implementation |
| --- | --- | --- |
| Entry and scene connection | Load the case configuration and connect all extension components | [`main.py`](main.py), [`case_setup.py`](case_setup.py) |
| Configuration | Constellation, users, timing, IDS mode, physical layer, and output settings | [`src/configuration/simulation_config.py`](src/configuration/simulation_config.py) |
| Experiment data | Fixed user locations, payload libraries, and fixed IDS test set | [`experiment/data/`](experiment/data/) |
| IDS methods | Signature, Heuristic, and Deep Learning detectors | [`experiment/ids/`](experiment/ids/) |
| Active behaviors | Malicious traffic and benign port `22` traffic | [`src/behaviors/`](src/behaviors/) |
| Application layer | Port `22` processing and execution of IDS decisions | [`src/stack/application_layer.py`](src/stack/application_layer.py) |
| Satellite integration | Install the selected IDS engine and record events | [`experiment/integration/`](experiment/integration/) |
| Result evaluation | Calculate fixed test set and deployed scenario metrics | [`experiment/evaluation/`](experiment/evaluation/) |
| Plotting | Generate the two Case 1 paper figures | [`plotting/`](plotting/) |

## 2. Final Directory Structure

The completed Case 1 directory structure is:

```text
cases/case1/
  main.py
  case_setup.py
  requirements.txt
  TUTORIAL.md
  __init__.py

  src/
    configuration/
      simulation_config.py
      simulation_config.default.py
      __init__.py
    behaviors/
      malicious_user_behavior.py
      normal_port22_behavior.py
      __init__.py
    stack/
      application_layer.py
      __init__.py
    __init__.py

  experiment/
    data/
      malicious_code_library.py
      normal_payload_library.py
      test_dataset.py
      user_locations.py
      __init__.py
    ids/
      ids_signature.py
      ids_heuristic.py
      ids_deep_learning.py
      train_ids_deep_learning.py
      __init__.py
    evaluation/
      evaluate_test_dataset.py
      evaluate_case_scenario_events.py
      ids_metrics.py
      __init__.py
    integration/
      satellite_ids_engine.py
      ids_event_log.py
      __init__.py
    models/
      dl_ids_model.keras
    output/
      *.csv
    __init__.py

  plotting/
    plot_ids_detection_rates.py
    plot_packet_loss_rate.py
    figures/
      fig6_detection_rates.png
      fig6_packet_loss_rate.png
```

These directories have different responsibilities.

```text
src/
```

Contains code that is directly connected to the EasySatSim simulation process. In this case, it mainly includes the case configuration, active user behaviors, and the application layer port `22` service.

```text
experiment/
```

Contains materials created for this experiment, including payload libraries, IDS methods, training programs, evaluation programs, model files, event logs, and network result CSV files. The `integration/` subdirectory is also placed here because its code connects the IDS methods to the satellite entities used in this case.

```text
plotting/
```

Contains only plotting programs and generated PNG figures. The plotting programs read experiment results from `experiment/output/` and save figures to `plotting/figures/`.

This separation is intentional:

```text
src/          how the case extends the simulator
experiment/   what the case evaluates
plotting/     how the paper figures are generated
```

## 3. Step 1: Create the Case Entry and Configuration Directory

### Goal

The first step is to create an independent entry point for Case 1. The case continues to use the EasySatSim simulation code from the project root, but loads its dedicated configuration file from:

```text
cases/case1/src/configuration/
```

This allows Case 1 to change constellation parameters, user count, running time, IDS mode, and output path without modifying the global configuration used by other examples or the main simulator.

### Files to Add

First create:

```text
cases/case1/
  main.py
  case_setup.py
  src/
    configuration/
      simulation_config.py
      simulation_config.default.py
      __init__.py
    __init__.py
```

At this stage, `case_setup.py` can contain only a minimal implementation. Later steps will gradually add fixed user location assignment, behavior registration, port `22` service registration, and satellite IDS installation.

### Write the Case Configuration

The dedicated case configuration file is:

```text
cases/case1/src/configuration/simulation_config.py
```

This file should follow the normal EasySatSim configuration style and add case specific parameters on top of it.

Important parameters include:

```python
import os
import numpy as np

IDS_MODE = os.environ.get("EASYSATSIM_INTRUSION_IDS", "signature").lower()
OUTPUT_PREFIX = os.environ.get("EASYSATSIM_INTRUSION_OUTPUT_PREFIX", IDS_MODE)

ORBIT_NUMBER = 40
SATELLITE_NUMBER_PRE_ORBIT = 33
ORBIT_INCLINATION = 50.88
ORBIT_HEIGHT = 1325
USER_NUMBER = 1000
SATELLITE_CONE_ANGLE = 50

CASE_MALICIOUS_USER_NUMBER = 20
CASE_ATTACK_START_TIME = 100
CASE_ATTACK_END_TIME = 500
CASE_SIMULATION_END_TIME = 800

USER_LATITUDE_MIN = -70
USER_LATITUDE_MAX = 70

CASE_ATTACK_PROBABILITY = 0.7
CASE_MALICIOUS_BEHAVIOR_INTERVAL = 5.0

CASE_ENABLE_NORMAL_PORT22_TRAFFIC = True
CASE_NORMAL_PORT22_START_TIME = CASE_ATTACK_START_TIME
CASE_NORMAL_PORT22_END_TIME = CASE_ATTACK_END_TIME
CASE_NORMAL_PORT22_BEHAVIOR_INTERVAL = 10.0
CASE_NORMAL_PORT22_PROBABILITY = 0.02

CASE_DL_THRESHOLD = 0.9

SAVE_FILE_PATH = f"../cases/case1/experiment/output/{OUTPUT_PREFIX}.csv"

TOTAL_SATELLITE_NUMBER = ORBIT_NUMBER * SATELLITE_NUMBER_PRE_ORBIT
COVER_RADIUS = np.tan(np.radians(SATELLITE_CONE_ANGLE / 2)) * ORBIT_HEIGHT
POPULATION_PATH = "../resource/population_matrix.npy"

CASE_RUNNING_TIME_REAL_SECONDS = CASE_SIMULATION_END_TIME
```

One important design choice is `IDS_MODE`. The case runs three IDS methods in the same scenario by changing only this environment variable:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="signature"
$env:EASYSATSIM_INTRUSION_IDS="heuristic"
$env:EASYSATSIM_INTRUSION_IDS="dl"
```

The output path also depends on the IDS mode, so the network result CSV files for the three IDS modes can be saved separately.

If the configuration is not overridden through an environment variable, the current default mode is `signature`, and the initial generic output path is `signature.csv`. When the user starts the simulation in the interactive interface, EasySatSim automatically replaces this generic path with a timestamped path based on `OUTPUT_PREFIX` that does not conflict with existing results.

### Write the Initial `case_setup.py`

Create:

```text
cases/case1/case_setup.py
```

At the beginning, it only needs to define a function that will later connect case specific components to the scene:

```python
from configuration import simulation_config as cg
from src.tools.config_loader import load_configuration


if not hasattr(cg, "CASE_MALICIOUS_USER_NUMBER"):
    cg = load_configuration("cases/case1/src")


def configure_case1_scene(scene_controller, ids_mode=None, reset_event_log=True):
    return {
        "ids_mode": ids_mode or cg.IDS_MODE,
    }


def configure_scene(scene_controller):
    return configure_case1_scene(scene_controller=scene_controller)
```

This placeholder keeps the interface unchanged. Even as the internal implementation grows in later steps, other code can continue to call:

```python
configure_case1_scene(sc)
```

### Write the Case Entry Point

Create:

```text
cases/case1/main.py
```

The entry program should load the dedicated Case 1 configuration before importing `configuration.simulation_config`:

```python
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.config_loader import load_configuration
load_configuration("cases/case1/src")
from configuration import simulation_config as cg
from cases.case1.case_setup import configure_case1_scene
from src.simulation.controller.scene_controller import SceneController


def main():
    sc = SceneController()
    sc.create_scene()
    sc.default_behavior()
    sc.default_stack()
    configure_case1_scene(sc)
    sc.configuration_complete()
    sc.run_simulation(plotter=True, running_time=cg.CASE_RUNNING_TIME_REAL_SECONDS)


if __name__ == "__main__":
    main()
```

This `sys.path` handling is necessary because Case 1 also contains `cases/case1/src/`. When:

```text
python cases\case1\main.py
```

is used, Python may otherwise treat the `src/` directory inside the case as the top level simulator package. Placing the project root at the beginning of the import path ensures that imports such as:

```python
src.tools.config_loader
```

always refer to the EasySatSim main project source tree.

### Verify This Step

Run the following command from the project root:

```powershell
python -c "from cases.case1 import main; print(main.cg.USER_NUMBER); print(main.cg.SAVE_FILE_PATH)"
```

Expected result:

```text
1000
../cases/case1/experiment/output/<ids-mode>.csv
```

The exact filename may differ if the visualization interface has already assigned a timestamped output path. The important point is that the result path should refer to:

```text
cases/case1/experiment/output/
```

You can also check whether the case compiles successfully:

```powershell
python -m compileall -q cases\case1
```

At this point, Case 1 has its own entry point and configuration. The following steps add data files, IDS methods, user behaviors, the application layer service, satellite side integration, evaluation programs, and plotting programs.

## 4. Step 2: Add Fixed User Locations

### Goal

EasySatSim can generate user locations automatically, but Case 1 uses fixed coordinates so that repeated experiments preserve the same spatial distribution of malicious and normal users.

This avoids changing the IDS comparison merely because user locations change and users therefore access different satellites.

### Files to Add

Create:

```text
cases/case1/experiment/data/
  user_locations.py
  __init__.py
```

This file defines two lists:

```python
locations_malicious_users = [
    # 20 malicious user coordinates
]

locations_normal_users = [
    # 980 normal user coordinates
]
```

The current case uses:

```text
20 malicious users
980 normal users
1000 users
```

The first 20 users in the simulator are treated as malicious users, and the remaining users are treated as normal users.

### Connect the Fixed Locations to the Scene

Add the following to `case_setup.py`:

```python
from cases.case1.experiment.data.user_locations import locations_malicious_users
from cases.case1.experiment.data.user_locations import locations_normal_users


def assign_case1_user_locations(users):
    malicious_count = cg.CASE_MALICIOUS_USER_NUMBER
    all_locations = list(locations_malicious_users) + list(locations_normal_users)

    if len(locations_malicious_users) != malicious_count:
        raise ValueError("The malicious user count and location list do not match.")
    if cg.USER_NUMBER != len(all_locations):
        raise ValueError("USER_NUMBER and the total location count do not match.")
    if len(users) != len(all_locations):
        raise ValueError("The scene user count and the location count do not match.")

    for i, malicious_user in enumerate(users[:malicious_count]):
        latitude, longitude = locations_malicious_users[i]
        malicious_user.set_position(latitude, longitude)

    for i, normal_user in enumerate(users[malicious_count:]):
        latitude, longitude = locations_normal_users[i]
        normal_user.set_position(latitude, longitude)
```

These checks are useful in tutorial code. If the configuration declares:

```python
USER_NUMBER = 1000
```

but the coordinate file provides a different number of user locations, the program reports the problem before the scene runs.

### Update the Scene Configuration Function

Inside `configure_case1_scene`, obtain the user list and call the location assignment function:

```python
entity_manager = scene_controller.get_entity_manager()
users = entity_manager.get_entity(entity_category="user")

assign_case1_user_locations(users=users)
```

### Verify This Step

Run the lightweight import check:

```powershell
python -c "from cases.case1.experiment.data.user_locations import locations_malicious_users, locations_normal_users; print(len(locations_malicious_users), len(locations_normal_users))"
```

Expected result:

```text
20 980
```

Then compile the entire case again:

```powershell
python -m compileall -q cases\case1
```

## 5. Step 3: Add Malicious and Benign Payload Libraries

### Goal

The IDS methods and traffic behaviors need reproducible payload sources. Therefore, this case stores malicious and benign payloads in separate data files.

The malicious payload library is used by malicious users during the satellite network simulation.

The benign payload library is used both for IDS training/testing and for benign port `22` traffic in the case scenario.

### Files to Add

Create:

```text
cases/case1/experiment/data/
  malicious_code_library.py
  normal_payload_library.py
```

`malicious_code_library.py` should export:

```python
malicious_code_library = [
    # attack payload strings
]
```

`normal_payload_library.py` should export:

```python
normal_payload_library = [
    # normal application payload strings
]

normal_port22_payload_library = [
    # benign port-22 payload strings used in the case scenario
]
```

The current case contains:

```text
200 malicious payloads
200 normal payloads
207 benign port 22 payloads
```

### Design Notes

These data should remain simple and explicit. The purpose of this case is not to build a production cybersecurity dataset. Instead, it provides a controlled scenario in which three IDS methods exhibit different detection behavior while sharing the same EasySatSim simulation scenario.

The malicious payload library should contain both payloads that can be matched easily by simple signatures and payloads that require more general matching methods.

The benign payload library should contain ordinary text payloads as well as a small number of benign payloads that may be judged suspicious by more aggressive detectors. This makes the false positive calculation meaningful.

### Verify This Step

Run:

```powershell
python -c "from cases.case1.experiment.data.malicious_code_library import malicious_code_library; from cases.case1.experiment.data.normal_payload_library import normal_payload_library, normal_port22_payload_library; print(len(malicious_code_library), len(normal_payload_library), len(normal_port22_payload_library))"
```

Expected result:

```text
200 200 207
```

## 6. Step 4: Add a Fixed Test Dataset

### Goal

The paper compares IDS behavior in two places:

- a fixed test set;
- the satellite network case scenario.

To keep the comparison consistent, all three IDS methods must be evaluated on the same test set. The test set should also be separate from the training data used by the deep learning model.

### File to Add

Create:

```text
cases/case1/experiment/data/test_dataset.py
```

This file imports the payload libraries and provides fixed malicious and benign test samples:

```python
from cases.case1.experiment.data.malicious_code_library import malicious_code_library
from cases.case1.experiment.data.normal_payload_library import normal_payload_library


test_malicious_payloads = malicious_code_library
test_benign_payloads = normal_payload_library[:40]

TEST_DATASET_PROFILE = {
    "malicious": len(test_malicious_payloads),
    "benign": len(test_benign_payloads),
    "total": len(test_malicious_payloads) + len(test_benign_payloads),
}
```

The current fixed test set contains:

```text
200 malicious samples
40 benign samples
240 samples
```

### Why Use a Fixed Test Set?

The test set result mainly reflects the behavior of the IDS implementation itself and the selected payload collection. It should not be affected by satellite coverage, routing, or packet loss.

The result in the case scenario is calculated in later steps from events generated by the actual satellite simulation.

Keeping these two types of results separate makes the meaning of the metrics in the figure clear:

```text
test-set detection rate       IDS behavior on a static payload test set
case-scenario detection rate  IDS behavior after deployment in the EasySatSim scenario
case-scenario false positives benign port 22 traffic incorrectly blocked in the scenario
```

### Verify This Step

Run:

```powershell
python -c "from cases.case1.experiment.data.test_dataset import TEST_DATASET_PROFILE; print(TEST_DATASET_PROFILE)"
```

Expected result:

```text
{'malicious': 200, 'benign': 40, 'total': 240}
```

## 7. Step 5: Add Three IDS Methods

### Goal

This step adds the three IDS implementations used in the experiment. Each IDS is intentionally kept small and easy to inspect.

Because this case is used both as a tutorial and for reproducing the paper experiment, the code prioritizes readability.

### Files to Add

Create:

```text
cases/case1/experiment/ids/
  ids_signature.py
  ids_heuristic.py
  ids_deep_learning.py
  train_ids_deep_learning.py
  __init__.py
```

### Signature IDS

`ids_signature.py` performs direct substring matching against a small set of known byte signatures:

```python
detection_rules = [
    "\x31\xc0\x50\x68\x2f\x2f\x73\x68",
    "\x31\xdb\xf7\xe3\xb0\x66",
]


def detect(code):
    for rule in detection_rules:
        if rule in code:
            return True, rule
    return False, None
```

The return value is:

```text
(detected, matched_rule)
```

This method detects only payloads that contain known signatures. Under the current case settings, it is expected to have the lowest detection rate among the three IDS methods.

### Heuristic IDS

`ids_heuristic.py` compares the payload being inspected against known malicious base samples and applies a set of heuristic rules:

```python
def detect(code):
    for base_code in knowledge_bases:
        matched_reasons = []
        match_scores = []
        for index, rule in enumerate(heuristic_rules):
            is_detected = rule(code, base_code)
            match_scores.append(is_detected)
            if is_detected:
                matched_reasons.append(heuristic_reason[index])

        similarity = sum(match_scores) / len(heuristic_rules)
        if similarity >= 0.5:
            return True, similarity, matched_reasons, base_code

    return False, 0, [], None
```

The return value is:

```text
(detected, similarity, matched_reasons, base_code)
```

Compared with signature matching, this method uses a less strict decision rule. It can therefore detect more malicious payload variants, but it is also more likely to classify some unusual benign traffic as malicious.

### Deep Learning IDS

`ids_deep_learning.py` uses TensorFlow/Keras. It first encodes each payload into a fixed length integer sequence and then passes it to a small neural network classifier:

```python
def encode_payload(payload, max_sequence_length=MAX_SEQUENCE_LENGTH):
    sequence = [min(ord(char), 255) + 1 for char in payload[:max_sequence_length]]
    if len(sequence) < max_sequence_length:
        sequence.extend([0] * (max_sequence_length - len(sequence)))
    return sequence
```

The runtime detection function is:

```python
def detect(code, model=None, threshold=DEFAULT_THRESHOLD):
    if model is None:
        model = get_runtime_model()
    score = predict_score(code, model)
    return score >= threshold, score
```

The return value is:

```text
(detected, score)
```

The trained model is saved to:

```text
cases/case1/experiment/models/dl_ids_model.keras
```

### Deep Learning IDS Training Entry

`train_ids_deep_learning.py` is used to train and save the model:

```python
from cases.case1.experiment.ids import ids_deep_learning
from cases.case1.experiment.evaluation.ids_metrics import evaluate_test_dataset
from cases.case1.experiment.evaluation.ids_metrics import print_test_metrics


def main():
    model = ids_deep_learning.train_and_save_model()
    metrics = evaluate_test_dataset(lambda payload: ids_deep_learning.detect(payload, model)[0])
    print(f"DL IDS model saved to: {ids_deep_learning.DEFAULT_MODEL_PATH}")
    print_test_metrics("Deep learning IDS saved-model evaluation", metrics)
    return ids_deep_learning.DEFAULT_MODEL_PATH
```

### Verify This Step

If a trained model already exists, first check whether the code compiles:

```powershell
python -m compileall -q cases\case1\experiment\ids
```

To retrain the deep learning IDS model, run:

```powershell
python -m cases.case1.experiment.ids.train_ids_deep_learning
```

This command requires TensorFlow. The required dependency is already included in:

```text
cases/case1/requirements.txt
```

## 8. Step 6: Add Fixed Test Set Evaluation

### Goal

Before deploying the three IDS methods in the satellite network case scenario, evaluate them on the same fixed test dataset.

This step generates the first metric file required by Figure 6(a):

```text
cases/case1/experiment/output/ids_test_set_metrics.csv
```

### Files to Add

Create:

```text
cases/case1/experiment/evaluation/
  ids_metrics.py
  evaluate_test_dataset.py
  __init__.py
```

### Add Shared Metric Functions

`ids_metrics.py` should provide an evaluation function that is independent of the specific IDS implementation:

```python
def evaluate_test_dataset(detect_func):
    true_positive = count_detected(detect_func, test_malicious_payloads)
    false_negative = len(test_malicious_payloads) - true_positive
    false_positive = count_detected(detect_func, test_benign_payloads)
    true_negative = len(test_benign_payloads) - false_positive
    total = true_positive + false_negative + false_positive + true_negative

    return {
        "tp": true_positive,
        "fn": false_negative,
        "fp": false_positive,
        "tn": true_negative,
        "accuracy": safe_rate(true_positive + true_negative, total),
        "detection_rate_test_set": safe_rate(true_positive, len(test_malicious_payloads)),
        "false_positive_rate_test_set": safe_rate(false_positive, len(test_benign_payloads)),
    }
```

This keeps the evaluation logic independent of the specific IDS implementation.

### Add the Test Set Evaluation Program

`evaluate_test_dataset.py` loads the three IDS methods and writes one row to the CSV for each method:

```python
results = [
    ("S-IDS", evaluate_test_dataset(lambda payload: ids_signature.detect(payload)[0])),
    ("HR-IDS", evaluate_test_dataset(lambda payload: ids_heuristic.detect(payload)[0])),
    ("DL-IDS", evaluate_test_dataset(lambda payload: ids_deep_learning.detect(payload, dl_model)[0])),
]
```

The CSV contains the following fields:

```text
ids
tp
fp
tn
fn
accuracy_test_set
detection_rate_test_set
false_positive_rate_test_set
test_malicious_total
test_benign_total
```

### Verify This Step

Run:

```powershell
python -m cases.case1.experiment.evaluation.evaluate_test_dataset
```

The expected qualitative result is:

```text
S-IDS: lower detection rate
HR-IDS: medium detection rate
DL-IDS: highest detection rate
```

The current example values are approximately:

```text
S-IDS: detection_test=40.00%
HR-IDS: detection_test=80.00%
DL-IDS: detection_test=92.00%
```

## 9. Step 7: Add Malicious User Behavior

### Goal

The case scenario requires malicious users to actively send attack payloads during the attack time window.

This functionality is implemented through an EasySatSim active behavior.

### File to Add

Create:

```text
cases/case1/src/behaviors/malicious_user_behavior.py
```

The behavior follows the EasySatSim behavior implementation style and sends malicious payloads to the satellite currently accessed by the user:

```python
class MaliciousUserActiveBehavior(AbstractBehavior):
    @staticmethod
    async def send_malicious_data(entity, data):
        current_time = np.ndarray((1,), dtype=np.float64, buffer=entity.shm_current_time.buf)
        if current_time[0] < cg.CASE_ATTACK_START_TIME or current_time[0] > cg.CASE_ATTACK_END_TIME:
            return

        attack_probability = cg.CASE_ATTACK_PROBABILITY if data is None else data
        if random.random() > attack_probability:
            return

        if entity.access_satellite is None:
            return
        if "*" not in entity.mac_table:
            return

        target_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
        message = random.choice(malicious_code_library)
```

The behavior then constructs a normal `DataMessage`, uses:

```python
StackFunc.encapsulate_message_to_signal
```

to complete protocol stack encapsulation, and places the result into the user's MAC buffer.

### Register and Bind the Behavior

Add two functions:

```python
def register_malicious_user_behavior(behavior_manager):
    behavior_manager.add_active_behavior(
        behavior_name=MALICIOUS_BEHAVIOR_NAME,
        behavior_func=MaliciousUserActiveBehavior.send_malicious_data,
        interval=cg.CASE_MALICIOUS_BEHAVIOR_INTERVAL,
        is_async=True,
        data=cg.CASE_ATTACK_PROBABILITY,
        last_run=None,
    )


def bind_malicious_user_behavior(entity_manager, behavior_manager, malicious_users):
    for malicious_user in malicious_users:
        malicious_user.clear_behaviors()
        entity_manager.bind_active_behavior(
            behavior_manager=behavior_manager,
            entity=malicious_user,
            behavior_name="simple_access_satellite",
        )
        entity_manager.bind_active_behavior(
            behavior_manager=behavior_manager,
            entity=malicious_user,
            behavior_name=MALICIOUS_BEHAVIOR_NAME,
        )
```

Malicious users retain the satellite access behavior, but their default traffic behavior is removed and replaced with the attack traffic behavior.

### Verify This Step

Compile:

```powershell
python -m compileall -q cases\case1\src\behaviors
```

## 10. Step 8: Add Benign Port 22 Background Traffic

### Goal

If the scenario contains only malicious traffic, the false positive rate in the deployed scenario cannot be calculated.

Therefore, the simulation also needs to generate benign traffic sent to port `22`.

### File to Add

Create:

```text
cases/case1/src/behaviors/normal_port22_behavior.py
```

This behavior is similar to the malicious user behavior, but it uses benign payloads and labels the ground truth as benign:

```python
data_others = {
    "source_port": source_port,
    "target_port": target_port,
    "source_ip": source_ip,
    "target_ip": target_ip,
    "next_hop_ip": next_hop_ip,
    "data_size_byte": data_size_byte,
    "delay": 0,
    "path": None,
    "ip_list": None,
    "ground_truth": GROUND_TRUTH_BENIGN,
}
```

The `ground_truth` field is written to the IDS event log in a later step.

### Register and Bind the Behavior

The registration function should respect the configuration switch:

```python
def register_normal_port22_behavior(behavior_manager):
    if not cg.CASE_ENABLE_NORMAL_PORT22_TRAFFIC:
        return
    behavior_manager.add_active_behavior(
        behavior_name=NORMAL_PORT22_BEHAVIOR_NAME,
        behavior_func=NormalPort22ActiveBehavior.send_normal_port22_data,
        interval=cg.CASE_NORMAL_PORT22_BEHAVIOR_INTERVAL,
        is_async=True,
        data=cg.CASE_NORMAL_PORT22_PROBABILITY,
        last_run=None,
    )
```

Then bind the behavior to normal users:

```python
def bind_normal_port22_behavior(entity_manager, behavior_manager, normal_users):
    if not cg.CASE_ENABLE_NORMAL_PORT22_TRAFFIC:
        return
    for normal_user in normal_users:
        entity_manager.bind_active_behavior(
            behavior_manager=behavior_manager,
            entity=normal_user,
            behavior_name=NORMAL_PORT22_BEHAVIOR_NAME,
        )
```

Normal users retain the EasySatSim default background traffic and additionally send benign port `22` traffic.

### Verify This Step

Run:

```powershell
python -m compileall -q cases\case1\src\behaviors
```

## 11. Step 9: Add the Port 22 Application Layer Service

### Goal

After malicious and benign port `22` packets reach a satellite, they need to be processed on the satellite.

This case implements the functionality by registering a case specific application layer protocol processing function for port `22`.

### File to Add

Create:

```text
cases/case1/src/stack/application_layer.py
```

### Add the Port 22 Protocol Processing Function

The protocol processing function reads the payload, builds the context, calls the satellite IDS engine, records the event, and stops further processing of the application message:

```python
class Port22IntrusionService(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_message: DataMessage = cross_layer_message.data
        shell_code = data_message.message
        context = build_intrusion_context(entity=entity, cross_layer_message=cross_layer_message)
        ids_engine = get_satellite_ids_engine(entity=entity)
        ids_result = ids_engine.inspect(payload=shell_code, context=context)
        action = apply_intrusion_result(
            entity=entity,
            ids_result=ids_result,
            ground_truth=context["ground_truth"],
        )
        ids_event = record_ids_event(
            context=context,
            ids_result=ids_result,
            action=action,
        )
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message
```

### Apply the Detection Result

This case preserves the original attack effect. If a malicious payload is not detected, the satellite executes the corresponding malicious effect and disconnects users:

```python
def apply_intrusion_result(entity, ids_result, ground_truth):
    detected = bool(ids_result["detected"])

    if ground_truth == GROUND_TRUTH_MALICIOUS:
        if detected:
            return "malicious_blocked"
        entity.disconnect_user()
        return "malicious_executed"

    if detected:
        return "benign_blocked"
    return "benign_allowed"
```

### Register Port 22

Add the registration function:

```python
def register_port22_application(stack_manager):
    stack_manager.add_protocol_func(
        layer_name="application",
        protocol_name=22,
        parse_func=Port22IntrusionService.parse_and_process_func,
        encapsulate_func=Port22IntrusionService.encapsulate_func,
    )
    stack_manager.add_relationship(
        layer_name="application",
        protocol_name=22,
        data_name="data_message",
    )
```

### Verify This Step

Run:

```powershell
python -m compileall -q cases\case1\src\stack
```

## 12. Step 10: Add Satellite Side IDS Integration

### Goal

The IDS should be installed on satellites. The processing flow in the scenario remains: packets first reach a satellite, and the satellite side IDS then inspects them.

### File to Add

Create:

```text
cases/case1/experiment/integration/satellite_ids_engine.py
```

### Implement a Unified IDS Engine

The engine normalizes the current IDS mode and dispatches the inspection task to the corresponding method:

```python
class SatelliteIDSEngine:
    _dl_model = None

    def __init__(self, ids_mode=None):
        self.ids_mode = normalize_ids_mode(ids_mode or cg.IDS_MODE)
        self.dl_threshold = cg.CASE_DL_THRESHOLD
        if self.ids_mode == IDS_MODE_DL:
            self._load_dl_model()

    def inspect(self, payload, context=None):
        if self.ids_mode == IDS_MODE_SIGNATURE:
            detected, matched_rule = ids_signature.detect(payload)
            return build_result(self.ids_mode, detected, detail=matched_rule)

        if self.ids_mode == IDS_MODE_HEURISTIC:
            detected, similarity, matched_reasons, base_code = ids_heuristic.detect(payload)
            return build_result(self.ids_mode, detected, score=similarity, detail=matched_reasons)

        if self.ids_mode == IDS_MODE_DL:
            from cases.case1.experiment.ids import ids_deep_learning
            model = self._load_dl_model()
            detected, score = ids_deep_learning.detect(payload, model=model, threshold=self.dl_threshold)
            return build_result(self.ids_mode, detected, score=score, detail="dl_score")
```

The actual file also supports:

```text
without_detection
```

as a control mode without detection.

### Install the IDS Engine on Satellites

Add:

```python
def install_satellite_ids(satellites, ids_mode=None):
    ids_mode = normalize_ids_mode(ids_mode or cg.IDS_MODE)
    for satellite in satellites:
        satellite.ids_engine = SatelliteIDSEngine(ids_mode=ids_mode)
```

After this function runs, the port `22` service can call:

```python
ids_engine = entity.ids_engine
ids_result = ids_engine.inspect(payload=shell_code, context=context)
```

to use the IDS engine installed on the current satellite.

### Verify This Step

Run:

```powershell
python -m compileall -q cases\case1\experiment\integration
```

## 13. Step 11: Add IDS Event Logging

### Goal

The detection rate and false positive rate in the case scenario must come from the completed satellite network simulation. Therefore, every port `22` IDS decision must be written to an event log.

### File to Add

Create:

```text
cases/case1/experiment/integration/ids_event_log.py
```

### Define Event Fields

The event log is stored as CSV. Each row contains the following fields:

```python
EVENT_FIELDNAMES = [
    "time",
    "ids",
    "ids_mode",
    "satellite_id",
    "source_ip",
    "target_ip",
    "target_port",
    "ground_truth",
    "detected",
    "action",
    "score",
    "detail",
]
```

`ground_truth` takes one of the following values:

```text
malicious
benign
```

`detected` is stored as text:

```text
1
0
```

### Write Events During Simulation

The main function is:

```python
def record_ids_event(context, ids_result, action, event_log_path=None):
    event = build_ids_event(context=context, ids_result=ids_result, action=action)
    path = Path(event_log_path) if event_log_path is not None else get_event_log_path(event["ids_mode"])
    write_ids_event(event=event, path=path)
    return event
```

By default, the event files for the three IDS methods are written to:

```text
cases/case1/experiment/output/ids_events_signature.csv
cases/case1/experiment/output/ids_events_heuristic.csv
cases/case1/experiment/output/ids_events_dl.csv
```

### Clear the Current Mode Log Before Each Run

Before starting a new case scenario run, reset the event file corresponding to the current IDS mode:

```python
def reset_ids_event_log(ids_mode=None, event_log_path=None):
    path = Path(event_log_path) if event_log_path is not None else get_event_log_path(ids_mode or cg.IDS_MODE)
    if path.exists():
        path.unlink()
```

This prevents events from a new run from being mixed with events left by an earlier run of the same IDS mode.

### Verify This Step

Compile:

```powershell
python -m compileall -q cases\case1\experiment\integration
```

## 14. Step 12: Connect All Components in `case_setup.py`

### Goal

After all components are available, `case_setup.py` connects them to the scene already created by EasySatSim. It performs the following tasks:

- assign fixed user locations;
- register the malicious user behavior;
- register the benign port `22` behavior;
- bind behaviors to users;
- install the currently selected IDS engine on satellites;
- register the port `22` application layer service;
- reset the IDS event log.

### Final Scene Configuration Function

The final `configure_case1_scene` function executes in the following order:

```python
def configure_case1_scene(scene_controller, ids_mode=None, reset_event_log=True):
    entity_manager = scene_controller.get_entity_manager()
    behavior_manager = scene_controller.get_behavior_manager()
    stack_manager = scene_controller.get_stack_manager()

    users = entity_manager.get_entity(entity_category="user")
    satellites = entity_manager.get_entity(entity_category="satellite")
    active_ids_mode = normalize_ids_mode(ids_mode or cg.IDS_MODE)

    assign_case1_user_locations(users=users)
    register_malicious_user_behavior(behavior_manager=behavior_manager)
    register_normal_port22_behavior(behavior_manager=behavior_manager)

    malicious_users = get_case1_malicious_users(users=users)
    normal_users = get_case1_normal_users(users=users)

    bind_malicious_user_behavior(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        malicious_users=malicious_users,
    )
    bind_normal_port22_behavior(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        normal_users=normal_users,
    )

    install_satellite_ids(satellites=satellites, ids_mode=active_ids_mode)
    register_port22_application(stack_manager=stack_manager)

    if reset_event_log:
        reset_ids_event_log(ids_mode=active_ids_mode)
```

The execution order matters:

- user locations must be assigned after the scene creates the users;
- behaviors must be registered before they are bound to users;
- IDS engines must be installed before port `22` traffic reaches satellites;
- the event log should be reset before the simulation starts.

### Verify This Step

Run:

```powershell
python -c "from cases.case1 import main; print(main.cg.USER_NUMBER); print(main.cg.IDS_MODE)"
python -m compileall -q cases\case1
```

## 15. Step 13: Run the Satellite Network Case Scenario

### Goal

Run the same 800 second scenario separately with the three IDS modes.

Only the IDS mode changes between the three runs.

### Commands

Run the following commands from the project root.

First, run Signature IDS:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="signature"
python cases\case1\main.py
```

Then run Heuristic IDS:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="heuristic"
python cases\case1\main.py
```

Finally, run Deep Learning IDS:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="dl"
python cases\case1\main.py
```

When the visualization window appears, click `Start` and wait for the simulation to finish. Do not start the next IDS mode until the window for the current IDS mode has stopped and its corresponding CSV file has been completely written.

### Expected Outputs

Each run generates one network result CSV under:

```text
cases/case1/experiment/output/
```

The filenames may be stable names:

```text
signature.csv
heuristic.csv
dl.csv
```

or timestamped files generated by the visualization interface:

```text
easysatsim_result_signature_*.csv
easysatsim_result_heuristic_*.csv
easysatsim_result_dl_*.csv
```

Each run also generates or replaces one event log corresponding to the current IDS mode:

```text
ids_events_signature.csv
ids_events_heuristic.csv
ids_events_dl.csv
```

### Notes

The complete Case 1 is designed to run for 800 seconds of wall time:

```python
CASE_RUNNING_TIME_REAL_SECONDS = CASE_SIMULATION_END_TIME
```

When generating the final results for the paper, this value should not be shortened arbitrarily unless the experimental settings and results in the paper are updated accordingly.

Therefore, each IDS mode takes approximately 13 minutes and 20 seconds of wall time, in addition to scene initialization and shutdown time. If the computer can generally keep pace with the configured timer, the complete experiment across all three IDS modes requires at least about 40 minutes.

## 16. Step 14: Calculate Case Scenario Metrics

### Goal

After the satellite network simulations for all three IDS modes have finished, calculate the detection rate and false positive rate from the event logs.

### File to Add

Create:

```text
cases/case1/experiment/evaluation/evaluate_case_scenario_events.py
```

This program reads:

```text
cases/case1/experiment/output/ids_events_*.csv
```

and generates:

```text
cases/case1/experiment/output/ids_case_scenario_metrics.csv
```

### Metric Definitions

For malicious events:

```text
detection_rate_case_scenario = true_positive / (true_positive + false_negative)
```

For benign events:

```text
false_positive_rate_case_scenario = false_positive / (false_positive + true_negative)
```

The program should calculate the confusion matrix from each row in the actual event logs:

```python
if ground_truth == GROUND_TRUTH_MALICIOUS:
    if detected:
        summary["true_positive"] += 1
    else:
        summary["false_negative"] += 1

if ground_truth == GROUND_TRUTH_BENIGN:
    if detected:
        summary["false_positive"] += 1
    else:
        summary["true_negative"] += 1
```

### Run

Execute:

```powershell
python -m cases.case1.experiment.evaluation.evaluate_case_scenario_events
```

The expected output should contain one row for each of the three IDS methods:

```text
S-IDS
HR-IDS
DL-IDS
```

## 17. Step 15: Plot IDS Detection Rates

### Goal

Figure 6(a) compares three metrics:

- detection rate on the fixed test set;
- detection rate after deployment in the Case 1 scenario;
- false positive rate in the Case 1 scenario.

The figure should read the metrics actually generated by the preceding evaluation programs.

### File to Add

Create:

```text
cases/case1/plotting/plot_ids_detection_rates.py
```

This program reads:

```text
cases/case1/experiment/output/ids_test_set_metrics.csv
cases/case1/experiment/output/ids_case_scenario_metrics.csv
```

and generates:

```text
cases/case1/plotting/figures/fig6_detection_rates.png
```

### Key Processing Logic

The plotting program reads the rows for the three IDS methods and extracts:

```python
test_detection = np.array([
    float(test_rows[ids]["detection_rate_test_set"]) for ids in IDS_LABELS
])

case_detection = np.array([
    float(case_rows[ids]["detection_rate_case_scenario"]) for ids in IDS_LABELS
])

case_false_positive = np.array([
    float(case_rows[ids]["false_positive_rate_case_scenario"]) for ids in IDS_LABELS
])
```

This ensures that Figure 6(a) remains linked to the metric CSV files generated in the previous steps.

### Run

Execute:

```powershell
python cases\case1\plotting\plot_ids_detection_rates.py
```

Expected output:

```text
cases/case1/plotting/figures/fig6_detection_rates.png
```

## 18. Step 16: Plot Packet Loss Rate

### Goal

Figure 6(b) compares the network layer packet loss rate under the three IDS modes.

This figure is calculated from the network result CSV files generated by the satellite network simulations, rather than from the IDS event logs.

### File to Add

Create:

```text
cases/case1/plotting/plot_packet_loss_rate.py
```

The program selects the newest matching CSV for each IDS mode from:

```text
cases/case1/experiment/output/
```

It supports both stable filenames:

```text
"signature.csv"
"heuristic.csv"
"dl.csv"
```

and timestamped filenames generated by the visualization interface:

```text
"easysatsim_result_signature_*.csv"
"easysatsim_result_heuristic_*.csv"
"easysatsim_result_dl_*.csv"
```

### Packet Loss Rate Definition

The figure uses packets completed in each second:

```text
packet_loss_rate =
Current_Lost_Packets_Number /
(Current_Lost_Packets_Number + Current_Arrived_Packets_Number)
```

The code is:

```python
completed_packets = arrived_packets + lost_packets
loss_rate = np.divide(
    lost_packets,
    completed_packets,
    out=np.zeros_like(lost_packets, dtype=float),
    where=completed_packets > 0,
)
```

The first 10 seconds are skipped when plotting:

```python
PLOT_WARMUP_SECONDS = 10
stable_mask = time_values >= PLOT_WARMUP_SECONDS
```

This avoids including initialization stage samples in the final curve.

### Run

Execute:

```powershell
python cases\case1\plotting\plot_packet_loss_rate.py
```

Expected output:

```text
cases/case1/plotting/figures/fig6_packet_loss_rate.png
```

## 19. Full Reproduction Workflow

Run all of the following commands from the EasySatSim repository root. The repository can be placed in any user directory or drive and does not require an author specific local path.

### 1. Prepare a Clean Reproduction Environment

If the Case 1 dependencies have not yet been installed, first run:

```powershell
python -m pip install -r cases/case1/requirements.txt
```

Before starting a new paper experiment, we recommend moving old Case 1 CSV files and figures to a separate backup directory or using a fresh repository copy. This prevents the packet loss plotting program from accidentally selecting a previously generated timestamped network CSV.

Unless you intend to retrain the model, do not delete:

```text
experiment/models/dl_ids_model.keras
```

Clear any IDS mode and output prefix environment variables left from an earlier PowerShell session:

```powershell
Remove-Item Env:EASYSATSIM_INTRUSION_IDS -ErrorAction SilentlyContinue
Remove-Item Env:EASYSATSIM_INTRUSION_OUTPUT_PREFIX -ErrorAction SilentlyContinue
```

Check the default IDS mode and generic output path:

```powershell
python -c "from cases.case1 import main; print(main.cg.IDS_MODE); print(main.cg.SAVE_FILE_PATH)"
```

The expected result is `signature` and an output file ending with:

```text
cases/case1/experiment/output/signature.csv
```

### 2. Check the Case 1 Source Code

```powershell
python -m compileall -q cases\case1
```

If the command finishes normally without a traceback, the syntax and basic import checks have passed.

### 3. Prepare the Deep Learning IDS Model

The current repository already includes the model used by this example, so retraining is normally unnecessary.

If you intentionally want to generate a new model, run:

```powershell
python -m cases.case1.experiment.ids.train_ids_deep_learning
```

Retraining may change the Deep Learning IDS reference results. After retraining, the fixed test set metrics, case scenario metrics, figures, and related values in the paper must therefore be regenerated.

### 4. Generate Fixed Test Set Metrics

```powershell
python -m cases.case1.experiment.evaluation.evaluate_test_dataset
```

Confirm that `ids_test_set_metrics.csv` contains exactly the following three IDS labels:

```text
S-IDS
HR-IDS
DL-IDS
```

### 5. Run the Three Satellite Network Case Scenarios

For each command below, wait for the visualization window to appear, click `Start`, and allow the full 800 second run to finish before proceeding to the next IDS mode.

Signature IDS:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="signature"
python cases\case1\main.py
```

Heuristic IDS:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="heuristic"
python cases\case1\main.py
```

Deep Learning IDS:

```powershell
$env:EASYSATSIM_INTRUSION_IDS="dl"
python cases\case1\main.py
```

After all three runs have finished, clear the IDS mode environment variable:

```powershell
Remove-Item Env:EASYSATSIM_INTRUSION_IDS -ErrorAction SilentlyContinue
```

### 6. Generate Deployed Scenario Metrics

```powershell
python -m cases.case1.experiment.evaluation.evaluate_case_scenario_events
```

### 7. Generate the Two Paper Figures

```powershell
python cases\case1\plotting\plot_ids_detection_rates.py
python cases\case1\plotting\plot_packet_loss_rate.py
```

The final figure files are:

```text
cases/case1/plotting/figures/fig6_detection_rates.png
cases/case1/plotting/figures/fig6_packet_loss_rate.png
```

## 20. Expected Outputs

### Output Checklist

After a complete reproduction, the following current outputs should be available:

| Output | Expected content |
| --- | --- |
| `ids_test_set_metrics.csv` | 3 rows: S-IDS, HR-IDS, and DL-IDS |
| `ids_events_signature.csv` | Nonempty Signature mode IDS events |
| `ids_events_heuristic.csv` | Nonempty Heuristic mode IDS events |
| `ids_events_dl.csv` | Nonempty Deep Learning mode IDS events |
| `ids_case_scenario_metrics.csv` | 3 deployed scenario metric rows |
| 3 network CSVs | One newest result for each IDS mode |
| `fig6_detection_rates.png` | Nonempty detection rate figure |
| `fig6_packet_loss_rate.png` | Nonempty packet loss rate figure |

The GUI normally names network result files:

```text
easysatsim_result_<mode>_<timestamp>.csv
```

The plotting programs also support stable filenames such as `signature.csv`.

### Structural Checks

- Each network CSV should contain the `Time`, `Current_Generated_Packets_Number`, `Current_Arrived_Packets_Number`, and `Current_Lost_Packets_Number` fields.
- A complete network CSV should cover approximately `0–799` simulation seconds and contain several hundred samples recorded by second.
- Each IDS event file should contain the `ground_truth`, `detected`, `action`, and `ids_mode` fields, and should contain both malicious and benign events.
- In `ids_case_scenario_metrics.csv`, `event_file_count` should be `1` for each of the three IDS labels.

### Reference Results

With the model included in the repository and the current fixed test set, the expected test set detection rates are:

| IDS | Test set detection rate |
| --- | --- |
| S-IDS | 40% |
| HR-IDS | 80% |
| DL-IDS | approximately 92% |

The deployed scenario contains random processes, so repeated runs may differ slightly. As a practical consistency check, S-IDS should have the lowest detection rate, HR-IDS should be higher, and DL-IDS should be highest. The current reference ranges are:

| IDS | Scenario detection rate reference range | False positive rate reference range |
| --- | --- | --- |
| S-IDS | 35%–50% | near 0% |
| HR-IDS | 70%–90% | below 3% |
| DL-IDS | 85%–100% | below 10% |

Small differences across platforms are acceptable, especially after retraining the Deep Learning IDS model.

## 21. Troubleshooting

### `ModuleNotFoundError: No module named 'src.tools'`

This error usually occurs because Python incorrectly treats:

```text
cases/case1/src/
```

as the top level `src` package.

To avoid this problem, the Case 1 entry program inserts the project root at the beginning of `sys.path` before importing EasySatSim simulation modules.

Run the case from the project root:

```powershell
python cases\case1\main.py
```

### IDS Event Logs Cannot Be Found

If the following command fails:

```powershell
python -m cases.case1.experiment.evaluation.evaluate_case_scenario_events
```

it usually means that the three scenario runs have not all finished, or the output directory does not contain:

```text
ids_events_signature.csv
ids_events_heuristic.csv
ids_events_dl.csv
```

Run `main.py` once for each IDS mode and click `Start` in the visualization window.

### Packet Loss Plotting Program Cannot Find CSV Files

`plot_packet_loss_rate.py` reads network result CSV files from:

```text
cases/case1/experiment/output/
```

Confirm that all three IDS modes have generated their corresponding results.

Stable filenames can be:

```text
signature.csv
heuristic.csv
dl.csv
```

They can also be timestamped visualization result files:

```text
easysatsim_result_signature_*.csv
easysatsim_result_heuristic_*.csv
easysatsim_result_dl_*.csv
```

If one IDS mode has multiple timestamped files, the plotting program selects the newest matching result according to file modification time. When preparing a clean paper reproduction, we recommend moving old run results out of the current output directory.

### A Run Was Closed Before 800 Seconds

An interrupted run may leave a short network CSV and an incomplete IDS event log. Do not mix these partial results with other completed IDS modes.

Simply rerun the same IDS mode. The scene configuration resets the stable event log corresponding to that mode, and the GUI creates a new timestamped network CSV. Before recalculating metrics, confirm that the new network result time axis has reached `799` seconds.

### Deep Learning IDS Model Cannot Be Found

If the DL IDS reports that the model is missing, retrain it:

```powershell
python -m cases.case1.experiment.ids.train_ids_deep_learning
```

The model should be saved to:

```text
cases/case1/experiment/models/dl_ids_model.keras
```

### User Count and Fixed Location Count Do Not Match

`case_setup.py` checks:

```text
USER_NUMBER = len(locations_malicious_users) + len(locations_normal_users)
CASE_MALICIOUS_USER_NUMBER = len(locations_malicious_users)
```

If either check fails, update:

```text
simulation_config.py
```

or:

```text
experiment/data/user_locations.py
```

so that the user count in the configuration matches the number of coordinates in the location lists.
