# EasySatSim Local Capacity Scan

This optional scan estimates a practical EasySatSim scale for the current
computer. The scan is a local hardware diagnostic. Its result depends on the computer.

## Install

Run from the repository root:

```powershell
python -m pip install -r tests/capacity_scan/requirements-capacity.txt
```

The scan uses the EasySatSim desktop visualization and therefore requires the
same PyQt5, VisPy, PyQtGraph, and OpenGL environment as the main program.

## Run

Close unrelated memory-intensive applications, then run:

```powershell
python tests/capacity_scan/run_capacity_scan.py
```

The default scan starts at 500 satellites, increases the constellation by 500
satellites, and stops at 15,000 satellites, a worker failure, or a memory
safety limit. Each scale uses a 5-second warm-up and a 20-second measurement.
Visualization windows open and close automatically; do not interact with them
while a measurement is running.

To verify the command and planned scales without starting a simulation:

```powershell
python tests/capacity_scan/run_capacity_scan.py --dry-run
```

For a short functional check of one scale:

```powershell
python tests/capacity_scan/run_capacity_scan.py --scales 500 --warmup-seconds 2 --measurement-seconds 3
```

The short command verifies the workflow only. Do not treat its measurements as
a stable capacity estimate.

## Test Definition

- Two fixed users are located in Beijing and Tokyo.
- The users exchange bidirectional test-mode traffic.
- The physical layer and live visualization are enabled.
- Every scale runs in a fresh process tree.
- Only the generated scan configuration is changed.

A scale is recommended only when all planned runs complete and the scale meets
all configured requirements:

- simulation time divided by wall time is at least 0.95;
- cumulative delivery ratio is at least 95 percent;
- generated workload is at least 80 percent of the 500-satellite baseline.

The scan stops when system memory reaches 85 percent used or available memory
falls to 2 GiB. Do not raise these limits merely to obtain a larger number.

## Read the Result

Each run creates:

```text
tests/capacity_scan/output/capacity_scan_<timestamp>/
```

Open `capacity_report.md` first. It contains the hardware information, tested
scales, result table, unmet requirements, and two different conclusions:

- **Recommended satellite count**: the largest continuous tested scale that
  satisfies all configured performance requirements.
- **Maximum supported satellite count**: the largest tested scale for which
  all planned workflows completed, even if its performance did not satisfy
  the recommendation requirements.

The maximum supported count can therefore be higher than the recommended
count. Both values apply only to the tested scales and the recorded test
environment.

Detailed audit data are retained in `capacity_runs.csv` and
`capacity_metadata.json`. Per-scale worker logs, raw network metrics, and
resource samples are stored in the corresponding `scale_*` directories.

## Optional Arguments

Run selected scales:

```powershell
python tests/capacity_scan/run_capacity_scan.py --scales 500 1000 1500 2000
```

Repeat every selected scale three times:

```powershell
python tests/capacity_scan/run_capacity_scan.py --scales 500 1000 1500 2000 --repeats 3
```

Regenerate a report from existing results without rerunning simulations:

```powershell
python tests/capacity_scan/run_capacity_scan.py --summarize-existing tests/capacity_scan/output/capacity_scan_<timestamp>
```

Use `--help` for all available thresholds and execution options.