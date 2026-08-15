# Case 2 Tutorial: Comparing Centralized and Federated Learning

This tutorial explains how Case 2 is built on top of EasySatSim. It is written
for readers who want to understand how to add a machine learning architecture
case study, not only how to run the finished scripts.

The case compares two learning architectures in the same LEO satellite network:

- `CL`: centralized learning. User devices upload training samples to a center
  server, and the server trains the model.
- `FL`: federated learning. User devices train local models, upload model
  parameters, and the center server aggregates them with FedAvg.

The implementation keeps the EasySatSim core unchanged. All case specific
configuration, behaviors, protocol stack messages, learning code, evaluation,
and plotting logic are placed under `cases/case2/`.

## Prerequisites

Run all commands from the EasySatSim project root. Install the complete Case 2
environment with:

```powershell
python -m pip install -r cases/case2/requirements.txt
```

This installs the core simulator, pandas and Matplotlib, and the verified
PyTorch/torchvision pair. PyTorch wheels vary by operating system and CPU/GPU
environment; use the appropriate PyTorch package source if the target platform
cannot install the pinned pair from its default package index.

## 1. Tutorial Goal

The goal of this case is to show how EasySatSim can be extended to study the
interaction between satellite networking and machine learning architecture
choices.

The final scenario contains:

- A Starlink S1 LEO constellation.
- 1000 ground users and one center server.
- A CIFAR-10 image classification task.
- A shared `SimpleCNN` model used by both CL and FL.
- A CL path where users send training samples through the satellite network.
- An FL path where the server sends global models and users upload local model
  updates through the satellite network.
- Non-IID user data partitions for FL.
- Learning logs for CL and FL accuracy over simulation time.
- Communication event logs for CL sample transfer checkpoints and FL model
  transfer events.
- Evaluation scripts that summarize throughput, latency, packet loss, and
  learning accuracy from generated CSV files.
- Plotting scripts that generate the two Figure 8 PNG files.

This organization keeps the simulator extension points visible:

```text
src/          how the case extends the EasySatSim simulation process
experiment/   what the case evaluates
plotting/     how the paper figures are generated
```

### How to Use This Tutorial

This document supports two reading paths:

- To reproduce the finished experiment, install the prerequisites and follow
  Sections 14-16. The implementation steps can be read later when a component
  needs to be understood or modified.
- To understand how a learning case is added to EasySatSim, follow Sections
  3-13 in order. Each step identifies the extension point, shows the important
  logic, and provides a verification method.

The implementation code blocks are focused excerpts. They explain the message
flow and design choices without duplicating every import, validation branch,
or serialization helper. The complete executable implementation is the source
file identified by each step and by the following map.

### EasySatSim Extension Map

| Layer | Case 2 addition | Complete implementation |
| --- | --- | --- |
| Entry and scene wiring | Select CL or FL and connect the selected architecture | [`main.py`](main.py), [`case_setup.py`](case_setup.py) |
| Configuration | Starlink S1 scene, learning mode, physical layer, training, and outputs | [`src/configuration/simulation_config.py`](src/configuration/simulation_config.py) |
| Dataset and partitioning | CIFAR-10 loading and deterministic non-IID user partitions | [`experiment/data/`](experiment/data/) |
| Shared model | SimpleCNN construction and `state_dict` serialization | [`experiment/learning/cnn_model.py`](experiment/learning/cnn_model.py) |
| CL extension | Sample messages, user/server behavior, and center server training | [`src/stack/cl_application.py`](src/stack/cl_application.py), [`src/behaviors/`](src/behaviors/), [`experiment/integration/cl_center_server.py`](experiment/integration/cl_center_server.py) |
| FL extension | Model messages, chunk transfer, local training, and FedAvg | [`src/stack/fl_application.py`](src/stack/fl_application.py), [`src/behaviors/`](src/behaviors/), [`experiment/integration/fl_center_server.py`](experiment/integration/fl_center_server.py) |
| Event logging | Learning metrics and communication checkpoints | [`experiment/integration/case2_event_logger.py`](experiment/integration/case2_event_logger.py) |
| Evaluation | Combine CL/FL learning and network measurements | [`experiment/evaluation/`](experiment/evaluation/) |
| Plotting | Generate the two Case 2 paper figures | [`plotting/`](plotting/) |

### CL and FL Data Flow

CL and FL reuse the same satellite network scenario and `SimpleCNN` model, but they differ in both the data transmitted through the network and the training process.

In **CL mode**, users first select training samples from their local CIFAR-10 data and encapsulate the samples as CL application layer messages. After processing by the EasySatSim protocol stack, the messages are sent through the satellite network to the center server. The center server receives and buffers these training samples. When the accumulated number of samples reaches the training condition, the server performs centralized CNN training using the received samples and records the training round, loss, test accuracy, and related results in `cl_learning_metrics.csv`.

In **FL mode**, the center server first serializes the current global model and divides it into multiple data chunks, which are sent through the satellite network to the users selected for the current round. After receiving the complete global model, each selected user trains the CNN on its own Non-IID local dataset. The resulting local model parameters are then serialized, divided into chunks, and uploaded through the satellite network to the center server. After receiving enough complete local model updates, the center server aggregates them using FedAvg and records the test accuracy and related results for each aggregation round in `fl_learning_metrics.csv`.

Therefore, CL mainly transmits **training samples** through the satellite network, whereas FL mainly transmits **global models and local model updates**. The network result CSV records network performance such as packet count, byte volume, latency, and packet loss generated by these communication processes. The learning result CSV records the model training process. The communication event logs record key events such as CL sample transfer checkpoints and FL model transmission and reception, which can be used to further analyze the network load produced by the two learning architectures.

## 2. Final Directory Structure

The finished case is organized as follows:

```text
cases/case2/
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
      cl_user_behavior.py
      cl_server_behavior.py
      fl_user_behavior.py
      fl_server_behavior.py
      __init__.py
    stack/
      cl_application.py
      fl_application.py
      __init__.py
    __init__.py

  experiment/
    data/
      README.md
      cifar10_data.py
      user_data_partition.py
      cifar-10-batches-py/       # generated local cache, ignored by Git
      cifar-10-python.tar.gz     # generated local cache, ignored by Git
      __init__.py
    learning/
      cnn_model.py
      __init__.py
    integration/
      case2_event_logger.py
      cl_center_server.py
      fl_center_server.py
      __init__.py
    evaluation/
      case2_metrics.py
      summarize_case2_results.py
      __init__.py
    models/
      __init__.py
    output/
      README.md
      cl_learning_metrics.csv
      fl_learning_metrics.csv
      cl_communication_events.csv
      fl_communication_events.csv
      case2_summary_metrics.csv
      easysatsim_result_*.csv
    __init__.py

  plotting/
    plot_learning_accuracy.py
    plot_network_performance.py
    plot_all_figures.py
    figures/
      fig8_accuracy.png
      fig8_network_performance.png
```

The generated CIFAR-10 archive and extracted directory are runtime artifacts.
They are not part of the EasySatSim source release. The Python loader and
partition modules remain tracked. See
`experiment/data/README.md` for the upstream source, checksums, dataset notice,
and local cache instructions. Case output CSV files are managed separately as
experiment results.

## 3. Step 1: Create the Case Entry and Configuration

### Goal

The first step is to create an isolated entry point. The case should use the
EasySatSim simulator code from the project root, but it should load its own
configuration from `cases/case2/src/configuration/`.

This allows the case to change constellation parameters, running time, learning
mode, ML parameters, and output paths without editing the global simulator
configuration.

### Files to Add

Create:

```text
cases/case2/
  main.py
  case_setup.py
  src/
    configuration/
      simulation_config.py
      simulation_config.default.py
      __init__.py
    __init__.py
```

### Write the Case Configuration

The active configuration file is:

```text
cases/case2/src/configuration/simulation_config.py
```

The key mode switch is:

```python
LEARNING_ARCHITECTURE = os.environ.get(
    "EASYSATSIM_LEARNING_ARCHITECTURE",
    "cl",
).lower()
OUTPUT_PREFIX = os.environ.get(
    "EASYSATSIM_ML_OUTPUT_PREFIX",
    LEARNING_ARCHITECTURE,
)
```

The same `main.py` is used for both CL and FL. The selected architecture comes
from the environment variable:

```powershell
$env:EASYSATSIM_LEARNING_ARCHITECTURE="cl"
```

or:

```powershell
$env:EASYSATSIM_LEARNING_ARCHITECTURE="fl"
```

The constellation uses a Starlink S1 setup:

```python
ORBIT_NUMBER = 72
SATELLITE_NUMBER_PRE_ORBIT = 22
ORBIT_INCLINATION = 53
ORBIT_HEIGHT = 550
USER_NUMBER = 1000
CASE_SIMULATION_END_TIME = 1000
```

The current CL specific parameters include:

```python
CL_SAMPLE_SEND_INTERVAL = 0.1
CL_SAMPLES_PER_MESSAGE = 1
CL_SAMPLE_BYTE_MODE = "float32_tensor"
CL_TRAIN_TRIGGER_SAMPLE_COUNT = 2000
CL_SERVER_TRAIN_EPOCHS = 2
CL_CLEAR_DEFAULT_USER_TRAFFIC = True
```

The current FL specific parameters include:

```python
FL_CLIENTS_PER_ROUND = 5
FL_UPDATES_PER_ROUND = FL_CLIENTS_PER_ROUND
FL_ENABLE_GLOBAL_MODEL_DOWNLINK = True
FL_DATA_PARTITION_MODE = "non_iid"
FL_MODEL_UPDATE_KIND = "full_state_dict"
FL_CHUNK_PAYLOAD_BYTE = 8192
FL_ROUND_TIMEOUT_SECONDS = 80
FL_MIN_UPDATES_PER_ROUND = 4
```

The initial network result path is mode dependent:

```python
SAVE_FILE_PATH = (
    f"../cases/case2/experiment/output/{OUTPUT_PREFIX}.csv"
)
```

This gives `cl.csv` or `fl.csv` before an interactive run starts. When the user
clicks `Start`, EasySatSim automatically assigns a nonconflicting timestamped
file such as `easysatsim_result_cl_<timestamp>.csv`. The learning and
communication logs continue to use their architecture specific stable names.

`simulation_config.default.py` is kept as a template and recovery reference.
The actual run uses `simulation_config.py`.

### Write the Case Entry Point

`main.py` loads the case specific configuration before importing
`configuration.simulation_config`:

```python
from src.tools.config_loader import load_configuration
load_configuration("cases/case2/src")
from configuration import simulation_config as cg
```

Then it creates the normal EasySatSim scene and calls the case setup function:

```python
sc = SceneController()
sc.create_scene()
sc.default_behavior()
sc.default_stack()
configure_case2_scene(sc)
sc.configuration_complete()
sc.run_simulation(plotter=True, running_time=cg.CASE_RUNNING_TIME_REAL_SECONDS)
```

The `sys.path` block at the top of `main.py` ensures that imports such as
`src.tools.config_loader` refer to the simulator source tree at the project
root, not to the case local `cases/case2/src/` package.

### Verify This Step

Run from the project root:

```powershell
python -c "from cases.case2 import main; print(main.cg.USER_NUMBER); print(main.cg.LEARNING_ARCHITECTURE)"
```

Expected output includes:

```text
1000
cl
```

The selected architecture may be `fl` if the environment variable is already
set.

## 4. Step 2: Add CIFAR-10 Data Loading

### Goal

Both CL and FL use the same CIFAR-10 task. Keeping the data loader in one file
makes the comparison fair: CL and FL share the same train/test split and the
same image transform.

### File to Add

Create:

```text
cases/case2/experiment/data/cifar10_data.py
```

This file provides:

```python
load_case2_cifar10(...)
get_dataset_targets(...)
get_cifar10_sample_payload_summary(...)
```

The loader applies:

```python
transforms.ToTensor()
transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
```

and splits the 50,000 CIFAR-10 training images into:

```python
CIFAR10_TRAIN_SPLIT = 45000
CIFAR10_TEST_SPLIT = 5000
```

The split is fixed by:

```python
CASE_RANDOM_SEED = 20260805
```

### Verify This Step

Compile the data module:

```powershell
python -m compileall -q cases\case2\experiment\data
```

The first full run may download CIFAR-10 if:

```python
CIFAR10_DOWNLOAD = True
```

The download is stored under `cases/case2/experiment/data/` for local reuse and
is ignored by Git. After the first successful download, verify the deterministic
45,000/5,000 split without running the simulation:

```powershell
python -c "from cases.case2.experiment.data.cifar10_data import load_case2_cifar10; d=load_case2_cifar10(download=False); print(len(d.train_dataset), len(d.test_dataset))"
```

Expected output is `45000 5000`. Dataset source, integrity values, and offline
instructions are documented in `cases/case2/experiment/data/README.md`.

## 5. Step 3: Add FL User Data Partitions

### Goal

FL should use non-IID user data.

### File to Add

Create:

```text
cases/case2/experiment/data/user_data_partition.py
```

This file builds fixed per user index lists from the training dataset. The
important configuration values are:

```python
FL_LOCAL_SAMPLE_COUNT = 3000
FL_DATA_PARTITION_MODE = "non_iid"
FL_PRIMARY_CLASSES_PER_USER = 2
FL_NON_IID_DOMINANT_FRACTION = 0.8
FL_PARTITION_WITH_REPLACEMENT = True
```

The current non-IID logic gives each user two primary classes and samples most
of that user's local data from those classes. This keeps the FL case simple but
still different from centralized training. The active scene rebuilds these
partitions deterministically in memory from `CASE_RANDOM_SEED`; it does not
require a pregenerated partition cache file.

### Verify This Step

Compile:

```powershell
python -m compileall -q cases\case2\experiment\data
```

The full FL run calls `build_case2_user_partitions(...)` through
`case_setup.py`.

## 6. Step 4: Add the Shared CNN Model

### Goal

CL and FL must use the same model architecture, otherwise the comparison would
mix architecture effects with network effects.

### File to Add

Create:

```text
cases/case2/experiment/learning/cnn_model.py
```

The shared model is `SimpleCNN`:

```text
conv1 -> ReLU -> MaxPool
conv2 -> ReLU -> MaxPool
fc1   -> ReLU
fc2
```

The model helper functions also provide parameter and serialization summaries:

```python
get_simple_cnn_parameter_count()
get_simple_cnn_raw_parameter_byte_size()
get_state_dict_serialized_size()
```

The current model has more than one million trainable parameters.

### Verify This Step

Run:

```powershell
python -c "from cases.case2.experiment.learning.cnn_model import get_simple_cnn_parameter_count; print(get_simple_cnn_parameter_count())"
```

Expected output:

```text
1070794
```

## 7. Step 5: Add Centralized Learning Messages and Behaviors

### Goal

In CL, each user periodically sends training samples to the center server. The
server buffers received samples and trains the shared CNN when enough samples
have arrived.

### Files to Add

Create:

```text
cases/case2/src/stack/cl_application.py
cases/case2/src/behaviors/cl_user_behavior.py
cases/case2/src/behaviors/cl_server_behavior.py
cases/case2/experiment/integration/cl_center_server.py
```

### CL Application Message

`cl_application.py` defines:

```python
@dataclass
class ClSampleMessage:
    image: torch.Tensor
    label: int
    index: int
```

The message can be serialized in two modes:

```text
uint8_image      -> about 3 KB per CIFAR-10 sample
float32_tensor   -> about 12 KB per CIFAR-10 sample
```

The active mode is:

```python
CL_SAMPLE_BYTE_MODE = "float32_tensor"
```

This tutorial case uses `float32_tensor` because CL represents uploading
training data to the center server. The received object is still a tensor, so
the server training code does not need a separate reconstruction step.

### CL User Behavior

`cl_user_behavior.py` defines `ClUserBehavior.send_training_samples(...)`.

The behavior:

```text
checks satellite access
selects the next local training sample
builds a ClSampleMessage
encapsulates it into the EasySatSim stack
puts it into the user's access satellite buffer
records packet generation
logs a checkpoint every CL_COMMUNICATION_LOG_INTERVAL samples
```

The sample index advances by user id and cursor:

```python
sample_index = (
    entity.entity_id
    + entity.case2_cl_sample_cursor * cg.USER_NUMBER
) % dataset_size
```

This avoids all users repeatedly sending the same early samples.

### CL Center Server

`cl_center_server.py` defines `ClCenterServer`. It is a case specific server
entity that can attach to satellites like a ground node and receive CL sample
messages.

The server stores:

```text
cl_sample_images
cl_sample_labels
cl_received_sample_count
cl_train_round
```

When the buffer reaches:

```python
CL_TRAIN_TRIGGER_SAMPLE_COUNT
```

the server builds a `TensorDataset`, trains the model, evaluates on the fixed
test split, and writes one row to `cl_learning_metrics.csv`.

### Verify This Step

Compile:

```powershell
python -m compileall -q cases\case2\src\stack cases\case2\src\behaviors cases\case2\experiment\integration
```

## 8. Step 6: Add Federated Learning Messages and Behaviors

### Goal

In FL, the server starts rounds, selects clients, sends the current global
model, receives local model updates, and aggregates received models with
FedAvg.

### Files to Add

Create:

```text
cases/case2/src/stack/fl_application.py
cases/case2/src/behaviors/fl_user_behavior.py
cases/case2/src/behaviors/fl_server_behavior.py
cases/case2/experiment/integration/fl_center_server.py
```

### FL Application Message

`fl_application.py` defines:

```python
@dataclass
class FlModelMessage:
    parameters: bytes
    user_id: int
    round_id: int
    message_type: int
    chunk_id: int = 0
    chunk_count: int = 1
    full_payload_byte: int = 0
```

There are two message types:

```text
FL_MESSAGE_TYPE_UPDATE  local model update uploaded by a user
FL_MESSAGE_TYPE_GLOBAL  global model sent by the server
```

The model payload is split before it enters the network stack:

```python
FL_CHUNK_PAYLOAD_BYTE = 8192
```

Each chunk is sent as an independent EasySatSim packet. The receiver caches
chunks by message type, round id, user id, and source IP. Only after all chunks
arrive does the receiver reconstruct the original serialized `state_dict`.

If a chunk is lost, the corresponding model transfer is not delivered to the
learning logic.

### FL User Behavior

`fl_user_behavior.py` defines:

```text
FlUserBehavior.train_local_model(...)
FlUserBehavior.send_model_update(...)
```

Each selected user trains a local copy of the global model on its own non-IID
partition, serializes the resulting `state_dict`, splits it into chunks, and
uploads the chunks through the satellite network.

### FL Center Server

`fl_center_server.py` defines `FlCenterServer`.

It manages:

```text
current FL round
selected user ids
expected updates
received updates
round timeout
FedAvg aggregation
test set evaluation
global model downlink
```

After the center server receives enough local model updates, it performs FedAvg aggregation on the uploaded `state_dict` objects. Specifically, the server first extracts the floating point parameters from each local model and averages the corresponding parameters from different users to obtain new global model parameters. The server then loads the aggregated parameters into the global model and evaluates the current global model on the fixed test set. Finally, the aggregation result, test accuracy, and related training information for the current round are written to `fl_learning_metrics.csv` for subsequent result analysis and plotting.

The round timeout prevents an incomplete model transfer from blocking all later
rounds. When a round reaches `FL_ROUND_TIMEOUT_SECONDS`, the server aggregates
the received updates only if their number is at least
`FL_MIN_UPDATES_PER_ROUND`. Otherwise, it records a `round_skipped` event,
clears the incomplete round state, and starts a new round at the next scheduled
server interval. A skipped round does not update the global model and does not
produce an accuracy row in `fl_learning_metrics.csv`.

### Verify This Step

Compile:

```powershell
python -m compileall -q cases\case2\src\stack cases\case2\src\behaviors cases\case2\experiment\integration
```

## 9. Step 7: Connect the Case in case_setup.py

### Goal

`case_setup.py` connects the case specific modules to the scene created by
EasySatSim.

### CL Configuration Flow

When:

```python
LEARNING_ARCHITECTURE = "cl"
```

the setup flow is:

```text
load_case2_cifar10(...)
-> reset CL learning and communication logs
-> register_cl_application(stack_manager)
-> register CL user/server behaviors
-> optionally clear default user traffic
-> bind user satellite access + CL sample sending + stack processing
-> create ClCenterServer
-> bind server satellite access + CL training + stack processing
```

### FL Configuration Flow

When:

```python
LEARNING_ARCHITECTURE = "fl"
```

the setup flow is:

```text
load_case2_cifar10(...)
-> build_case2_user_partitions(...)
-> reset FL learning and communication logs
-> register_fl_application(stack_manager)
-> register FL user/server behaviors
-> optionally clear default user traffic
-> bind user satellite access + local training + model upload + stack processing
-> create FlCenterServer
-> bind server satellite access + FL round management + stack processing
```

The function is idempotent. It stores a private flag on the scene controller so
the same scene is not configured twice.

### Verify This Step

Run:

```powershell
python -c "from cases.case2.case_setup import normalize_learning_architecture; print(normalize_learning_architecture('centralized_learning')); print(normalize_learning_architecture('federated_learning'))"
```

Expected output:

```text
cl
fl
```

## 10. Step 8: Add Event Logging

### Goal

The learning curves and communication summaries should come from generated
logs.

### File to Add

Create:

```text
cases/case2/experiment/integration/case2_event_logger.py
```

The logger writes:

```text
cl_learning_metrics.csv
fl_learning_metrics.csv
cl_communication_events.csv
fl_communication_events.csv
```

CL learning rows contain:

```text
Simulation_Time
Architecture
Train_Round
Received_Samples_Total
Used_Samples
Remaining_Buffered_Samples
Train_Loss
Test_Accuracy
```

FL learning rows contain:

```text
Simulation_Time
Architecture
Round_ID
Selected_Clients
Received_Updates
Aggregation_Reason
Test_Accuracy
```

Communication logs are intentionally not written for every CL sample. CL logs
checkpoints to keep long 1000 second runs from creating unnecessarily large
event files. FL logs model transfer events while the network CSV counts the
individual chunks.

### Verify This Step

```powershell
python -c "from cases.case2.experiment.integration.case2_event_logger import CL_LEARNING_TITLE_ROW, FL_LEARNING_TITLE_ROW, CL_COMMUNICATION_TITLE_ROW, FL_COMMUNICATION_TITLE_ROW; print(CL_LEARNING_TITLE_ROW[-1], FL_LEARNING_TITLE_ROW[-1], len(CL_COMMUNICATION_TITLE_ROW), len(FL_COMMUNICATION_TITLE_ROW))"
```

Expected output:

```text
Test_Accuracy Test_Accuracy 11 9
```

## 11. Step 9: Run CL and FL Simulations

### Goal

Run the same 1000 second satellite network scenario once for CL and once for
FL. Only the learning architecture changes between runs.

### Run CL

From the project root:

```powershell
$env:EASYSATSIM_LEARNING_ARCHITECTURE="cl"
python cases\case2\main.py
```

When the visualization window appears, click `Start` and wait until the
simulation finishes. Do not start FL until the CL window has stopped and its
network CSV has been written.

Expected outputs include:

```text
cases/case2/experiment/output/cl_learning_metrics.csv
cases/case2/experiment/output/cl_communication_events.csv
cases/case2/experiment/output/easysatsim_result_cl_*.csv
```

### Run FL

Then run:

```powershell
$env:EASYSATSIM_LEARNING_ARCHITECTURE="fl"
python cases\case2\main.py
```

Expected outputs include:

```text
cases/case2/experiment/output/fl_learning_metrics.csv
cases/case2/experiment/output/fl_communication_events.csv
cases/case2/experiment/output/easysatsim_result_fl_*.csv
```

The visualization window may generate timestamped network result files. The
evaluation script automatically selects the latest matching CL and FL network
CSV files. Each mode is configured for 1000 seconds, so it requires at least 16
minutes 40 seconds of wall clock simulation time, plus dataset loading,
training, aggregation, initialization, and shutdown. The two mode experiment
therefore requires at least 33 minutes 20 seconds and may take longer on a
CPU only or resource constrained machine.

## 12. Step 10: Summarize Results

### Goal

After both CL and FL finish, summarize network and learning metrics into one
CSV.

### File to Add

Create:

```text
cases/case2/experiment/evaluation/case2_metrics.py
cases/case2/experiment/evaluation/summarize_case2_results.py
```

The summary script reads:

```text
latest CL network CSV
latest FL network CSV
cl_learning_metrics.csv
fl_learning_metrics.csv
cl_communication_events.csv
fl_communication_events.csv
```

and writes:

```text
cases/case2/experiment/output/case2_summary_metrics.csv
```

### Metric Definitions

The default warmup is:

```python
DEFAULT_WARMUP_SECONDS = 10
```

Throughput is calculated from cumulative byte deltas after warmup:

```text
average_goodput_mbps =
    arrived_byte_after_warmup * 8 / effective_duration / 1e6

average_generated_throughput_mbps =
    generated_byte_after_warmup * 8 / effective_duration / 1e6
```

Packet loss is calculated from cumulative packet count deltas:

```text
packet_loss_rate =
    lost_packets_after_warmup / generated_packets_after_warmup
```

The final average latency is read from `Total_Latency`, because EasySatSim
stores this field as a cumulative average latency.

### Run

```powershell
python -m cases.case2.experiment.evaluation.summarize_case2_results
```

The command prints a one line summary for CL and FL and writes
`case2_summary_metrics.csv`.

## 13. Step 11: Generate Figure 8

### Goal

Generate the two figures used by the case:

```text
fig8_accuracy.png
fig8_network_performance.png
```

### Files to Add

Create:

```text
cases/case2/plotting/plot_learning_accuracy.py
cases/case2/plotting/plot_network_performance.py
cases/case2/plotting/plot_all_figures.py
```

### Accuracy Figure

`plot_learning_accuracy.py` reads:

```text
cl_learning_metrics.csv
fl_learning_metrics.csv
```

and writes:

```text
cases/case2/plotting/figures/fig8_accuracy.png
```

It plots test accuracy over simulation time.

### Network Figure

`plot_network_performance.py` refreshes `case2_summary_metrics.csv`, reads CL
and FL throughput/latency values, and writes:

```text
cases/case2/plotting/figures/fig8_network_performance.png
```

### Run

Generate both figures with:

```powershell
python -m cases.case2.plotting.plot_all_figures
```

## 14. Full Reproduction Workflow

Run all commands from the EasySatSim repository root. The repository may be
placed in any user directory or drive; no author specific path is required.

### 1. Prepare a Clean Reproduction

Install the complete Case 2 environment:

```powershell
python -m pip install -r cases/case2/requirements.txt
```

Move old Case 2 result CSVs and figures to a separate backup directory, or use
a fresh checkout. Keep a verified CIFAR-10 cache if it should be reused; the
dataset archive and extracted images are inputs, not experiment results. A
clean output directory prevents the summary code from selecting an older
timestamped CL or FL network CSV.

Clear architecture overrides left by an earlier PowerShell session:

```powershell
Remove-Item Env:EASYSATSIM_LEARNING_ARCHITECTURE -ErrorAction SilentlyContinue
Remove-Item Env:EASYSATSIM_ML_OUTPUT_PREFIX -ErrorAction SilentlyContinue
```

Confirm the default architecture and generic output path:

```powershell
python -c "from cases.case2 import main; print(main.cg.LEARNING_ARCHITECTURE); print(main.cg.SAVE_FILE_PATH)"
```

Expected values are `cl` and a path ending in
`cases/case2/experiment/output/cl.csv`.

### 2. Check the Sources, Dataset, and Model

```powershell
python -m compileall -q cases\case2
```

A successful command exits without a traceback.

On the first machine, download and verify CIFAR-10:

```powershell
python -c "from cases.case2.experiment.data.cifar10_data import load_case2_cifar10; d=load_case2_cifar10(download=True); print(len(d.train_dataset), len(d.test_dataset))"
```

On a machine with an existing verified cache, use `download=False`. The
expected split is always:

```text
45000 5000
```

Confirm the shared CNN definition:

```powershell
python -c "from cases.case2.experiment.learning.cnn_model import get_simple_cnn_parameter_count; print(get_simple_cnn_parameter_count())"
```

Expected output is `1070794`.

### 3. Run Centralized Learning

```powershell
$env:EASYSATSIM_LEARNING_ARCHITECTURE="cl"
python cases\case2\main.py
```

When the window appears, click `Start` and allow the 1000 second run to finish.
Confirm that the CL learning, communication, and network CSVs were written
before continuing.

### 4. Run Federated Learning

```powershell
$env:EASYSATSIM_LEARNING_ARCHITECTURE="fl"
python cases\case2\main.py
```

Again click `Start` and wait for the complete 1000 second run. Then clear the
override:

```powershell
Remove-Item Env:EASYSATSIM_LEARNING_ARCHITECTURE -ErrorAction SilentlyContinue
```

The two simulations require at least 33 minutes 20 seconds of configured
wall clock simulation time in total. Dataset loading and repeated CNN training
can make the complete workflow longer.

### 5. Summarize CL and FL Results

```powershell
python -m cases.case2.experiment.evaluation.summarize_case2_results
```

The command should report one `CL` row and one `FL` row and write
`case2_summary_metrics.csv`.

### 6. Generate Both Figures

```powershell
python -m cases.case2.plotting.plot_all_figures
```

Final figure files:

```text
cases/case2/plotting/figures/fig8_accuracy.png
cases/case2/plotting/figures/fig8_network_performance.png
```

The plotting entry refreshes `case2_summary_metrics.csv` before drawing the
network figure, so its console output should again identify both
architectures.

## 15. Expected Outputs and Acceptance Criteria

### Output Checklist

A complete reproduction should leave the following current outputs:

| Output | Expected content |
| --- | --- |
| `cl_learning_metrics.csv` | Nonempty CL training rounds |
| `fl_learning_metrics.csv` | Nonempty FL aggregation rounds |
| `cl_communication_events.csv` | CL sample transfer checkpoints |
| `fl_communication_events.csv` | FL global model and local update events |
| Two network CSVs | One newest result each for CL and FL |
| `case2_summary_metrics.csv` | One CL summary row and one FL summary row |
| `fig8_accuracy.png` | Nonempty CL/FL accuracy figure |
| `fig8_network_performance.png` | Nonempty throughput/latency figure |

The GUI normally names network results
`easysatsim_result_<architecture>_<timestamp>.csv`. The evaluator also accepts
stable `cl_network.csv` and `fl_network.csv` files.

### Structural Checks

- Both network CSVs should contain `Time`,
  `Current_Generated_Packets_Number`, `Current_Arrived_Packets_Number`, and
  `Current_Lost_Packets_Number` columns.
- A completed network result should reach approximately 1000 simulation
  seconds, contain roughly 1000 per second rows, and show approximately 1000
  covered users and 1584 operational satellites after initialization.
- CL learning rounds must increase monotonically and contain `Train_Loss` and
  `Test_Accuracy` values.
- FL round IDs must increase monotonically and record selected clients,
  received updates, aggregation reason, and test accuracy.
- CL communication logs should include `sample_sent_checkpoint` and
  `sample_received_checkpoint`.
- FL communication logs should include global model send/receive and
  local update send/receive events.
- The final summary must contain both `CL` and `FL`; a single architecture is
  not a complete comparison.

### Reference Results

With the current fixed split, seed, model, and configuration, the existing
paper scale run provides the following practical consistency ranges:

| Metric | CL reference | FL reference |
| --- | --- | --- |
| Completed learning rounds | 130-170 | 25-40 |
| Final test accuracy | 65%-80% | 55%-75% |
| Average goodput | 25-35 Mbps | 8-15 Mbps |
| Final average latency | 550-750 ms | 350-550 ms |
| Packet loss rate | 2%-5% | 1%-3% |

PyTorch, thread scheduling, hardware, and dependency versions can produce
differences. Empty logs, a truncated time axis, missing model transfer event
types, no completed FL rounds, or values far outside these ranges should be
investigated before the figures are used in the paper.

## 16. Troubleshooting

### `ModuleNotFoundError: No module named 'src.tools'`

Run the case from the project root:

```powershell
python cases\case2\main.py
```

The case entry point inserts the project root at the front of `sys.path`.
Running from unusual working directories can still confuse imports.

### CIFAR-10 Was Not Found

Install the Case 2 dependencies and keep automatic download enabled for the
first run:

```powershell
python -m pip install -r cases/case2/requirements.txt
```

```python
CIFAR10_DOWNLOAD = True
```

torchvision downloads and extracts CIFAR-10 under:

```text
cases/case2/experiment/data/
```

If the location is not writable, or an incomplete cache causes an integrity/permission error,
back up any required local data, correct the directory permissions or move the
incomplete cache, and retry. See `experiment/data/README.md` for checksums and
detailed troubleshooting.

### Summary Cannot Find CL or FL Network CSV

Run both simulations first. The summary script expects at least one CL network
CSV and one FL network CSV under:

```text
cases/case2/experiment/output/
```

Accepted names include:

```text
cl_network.csv
fl_network.csv
easysatsim_result_cl_*.csv
easysatsim_result_fl_*.csv
```

If several timestamped files exist, the summary selects the newest matching
file by modification time. Move older runs out of the output directory when
preparing a clean paper reproduction.

### A CL or FL Run Was Closed Early

An interrupted run can leave a short network CSV and partial stable learning
and communication logs. Do not combine that mode with a completed result from
the other architecture. Rerun the interrupted mode and confirm that its newest
network CSV reaches approximately 1000 seconds before summarizing. Case setup
resets the active architecture's stable learning and communication logs when a
new run is configured.

### FL Produces No Completed Rounds

Inspect `fl_communication_events.csv`. A usable run should contain
`global_model_sent`, `global_model_received`, `local_update_sent`, and
`local_update_received` events. If only send events appear, verify that the
model chunk size, physical layer settings, user coverage, and round timeout
still match the documented configuration. Do not lower the model size or
change the paper experiment merely to conceal an incomplete transfer.

### Figure Generation Fails

Make sure both learning metric files exist:

```text
cl_learning_metrics.csv
fl_learning_metrics.csv
```

Then run:

```powershell
python -m cases.case2.plotting.plot_all_figures
```
