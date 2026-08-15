# Getting Started

This guide explains how to install EasySatSim, start the default simulation, and locate the results from the first run. Run all commands from the repository root.

## 1. Requirements

EasySatSim is a Python desktop application. The current project has been tested with Python 3.13 on Windows. The main interface requires the following dependencies:

- NumPy;
- Numba;
- Colorama;
- Pillow;
- PyQt5;
- VisPy;
- PyQtGraph.

We recommend installing the main runtime dependencies in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install the following dependencies only when common result processing and plotting are needed:

```powershell
python -m pip install -r requirements-plotting.txt
```

The three complete cases provide separate dependency files. Case 1 additionally requires TensorFlow, Case 2 additionally requires PyTorch and torchvision, and Case 3 requires the common result processing and plotting dependencies:

```powershell
python -m pip install -r cases/case1/requirements.txt
python -m pip install -r cases/case2/requirements.txt
python -m pip install -r cases/case3/requirements.txt
```

PyTorch packages may differ across operating systems and CPU/GPU environments. The versions currently pinned for Case 2 are the combination that has been verified for this repository. If the target platform requires a different package source, please refer to the official PyTorch installation instructions.

On the first Case 2 run, torchvision downloads CIFAR-10. The downloaded archive and extracted data are used only as local cache files and are not included in the source repository. For the data source, checksums, offline use, and troubleshooting, see:

`cases/case2/experiment/data/README.md`

The IPv4/UDP example also provides a separate pinned dependency file:

```powershell
python -m pip install -r examples/protocol_ipv4_example/requirements.txt
```

These additional dependencies are needed only when running the corresponding case or example.

## 2. Verify the Installation

On a normal Windows desktop environment, we recommend running the independent small scale diagnostic before starting the complete default constellation:

```powershell
python tests/run_all.py
```

This check verifies the dependencies, Qt platform, OpenGL rendering, Dashboard, live refresh, a short simulation, and regression tests.

A successful desktop run should end with:

```text
PASS=14 FAIL=0 SKIP=0
Live release gate passed: True
```

Test reports, screenshots, and the short diagnostic CSV are written to `tests/artifacts/`.

For CI environments or machines without a visible desktop, use:

```powershell
python tests/run_all.py --mode offscreen
```

In this mode, the expected result for Step 6 is `SKIP`, so this mode cannot verify whether desktop OpenGL works correctly.

## 3. Run the Default Simulation

The default Starlink Phase I-A configuration is a complete simulation scenario with 32 orbital planes, 50 satellites per plane, 1,600 satellites in total, and 500 users. This configuration is mainly intended to demonstrate the complete EasySatSim runtime process.

From the project root, run:

```powershell
python -m src.main
```

After the program starts, the control window opens first. Before selecting `Simulation > Start Simulation`, you can review the current configuration summary, including:

- the number of orbital planes and satellites per plane;
- the total number of satellites and users;
- the network time step;
- the active configuration file;
- the planned result path.

The main configuration file is:

`configuration/simulation_config.py`

When each simulation starts, the program assigns a timestamped CSV path to the result file, so consecutive runs normally do not overwrite one another.

## 4. Choose a Supplied Configuration

Open:

`Configuration > Configuration Presets`

The current options are:

1. `Default (Starlink Phase I-A)`;
2. `Telesat T2`;
3. `Starlink S1`;
4. `Quarter-Starlink`;
5. `Select Configuration File...`;
6. `Save Current Configuration...`;
7. `Cancel`.

Preset configuration files are stored under `configuration/`. After a preset is selected, the program first validates its Python syntax and then copies it as the active `simulation_config.py`.

The file chooser displays only files matching `simulation_config*.py`.

When saving a custom preset, enter only the middle name. For example, entering:

```text
research_run
```

creates:

```text
configuration/simulation_config.research_run.py
```

## 5. Stop and Inspect a Run

Use:

`Simulation > Stop Simulation`

to stop the simulation worker processes.

After the simulation ends, the `Results` menu can be used to:

- export the result CSV;
- package the result, configuration, screenshot, log, and manifest together;
- open the result directory;
- save a screenshot.

The default result directory is:

`output/`

Results from each case are stored under the corresponding:

`cases/<case>/experiment/output/`

directory.

## 6. Run a Complete Case or Focused Example

The three cases are complete research scenarios:

```powershell
python cases/case1/main.py
python cases/case2/main.py
python cases/case3/main.py
```

Before running a complete experiment that may take a long time, we recommend reading the `TUTORIAL.md` in the corresponding case directory.

Case 2 also requires additional machine learning dependencies. Case 3 provides a separate paired random seed batch experiment workflow.

The IPv4/UDP integration is a focused example:

```powershell
python examples/protocol_ipv4_example/main.py
python examples/protocol_ipv4_example/show_result.py
```

## 7. Additional Verification

You can compile the simulator and the supplied scenarios without running a long simulation:

```powershell
python -m compileall -q src configuration cases examples
```

## Further Reading

- [Configuration Reference](configuration.md)
- [Architecture](architecture.md)
- [Visualization Guide](visualization.md)
- [Troubleshooting](troubleshooting.md)