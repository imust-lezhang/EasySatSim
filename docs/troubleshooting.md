# Troubleshooting

When diagnosing a problem, start with the **exact command that was run, the active configuration, the Run Log, and the complete exception information**. Do not change scientific parameters in an experiment merely to make an error disappear.

## `ModuleNotFoundError` for `src`, `cases`, or `examples`

Run commands from the repository root. For example:

```powershell
python -m src.main
python cases/case3/main.py
python -m cases.case3.experiment.evaluation.process_results
```

When a command depends on the project root being present in `sys.path`, do not use `cases/case3` as the current working directory.

## The Wrong Configuration Is Loaded

The main program uses:

```text
configuration/simulation_config.py
```

Each complete case uses its own:

```text
cases/<case>/src/configuration/simulation_config.py
```

When starting a case, run its `main.py` as documented so that the configuration loader activates the correct case configuration directory before simulation modules are imported.

In the interface, you can also check the path of the active configuration file on the overview page before simulation.

## A Configuration Preset Is Rejected

Selectable configuration files must match:

```text
simulation_config*.py
```

Their uppercase configuration field names and order must also match:

```text
simulation_config.default.py
```

If a preset in the main directory contains fields that belong only to a specific case, remove those case specific fields or use the configuration file provided by that complete case.

When saving a named preset, enter only the middle name. For example:

```text
test
```

Do not enter:

```text
simulation_config.test.py
```

The latter will be rejected.

## The Simulation Cannot Start

The interface checks numeric ranges, constellation totals, latitude ranges, rate tables, population data, and write access to the result output path.

If the simulation cannot start, first check the notification and `Run Log`, correct the reported field, and then start the simulation again.

Common causes include:

- orbit count, user count, rate, bandwidth, or time step values less than or equal to 0;
- `SATELLITE_CONE_ANGLE` outside the range `(0, 180)`;
- a minimum value greater than the corresponding maximum value;
- a missing population matrix file;
- an invalid or unwritable directory for `SAVE_FILE_PATH`.

## The Window, 3D View, or Live Visualization Cannot Open

EasySatSim uses **PyQt5** and **VisPy**. PyQt6 cannot directly replace PyQt5 in the current interface, and the visualization library is named `vispy`, not `Visby`.

We recommend running the layered diagnostics in a normal local Windows desktop session:

```powershell
python tests/run_all.py --mode live --timeout 90
```

Use the first failed Step to locate the problem:

- **Step 1**: a dependency may be missing or incompatible, different Qt bindings may be mixed, or a Qt platform plugin may be missing;
- **Step 3–4**: the problem may be related to the Qt application, event loop, display session, or `qwindows.dll`;
- **Step 5**: VisPy did not correctly select the PyQt5 backend;
- **Step 6**: the problem may be related to the OpenGL context, graphics driver, virtual machine, or remote desktop environment;
- **Step 7**: PyQtGraph drawing or updates may have failed;
- **Step 8–11**: the problem may be related to the EasySatSim Dashboard, shared state refresh, or short simulation integration.

In offscreen mode, a `SKIP` result for Step 6 does not prove that desktop OpenGL works correctly.

The live release validation requires:

```text
FAIL=0
SKIP=0
Live release gate passed: True
```

## A Stale Process or Shared Memory Error Appears

Under normal conditions, the interface terminates worker processes and waits for them to exit when a simulation is stopped, and it cleans stale named shared memory before the next run.

If a Python process or the interface is forcibly terminated, close any remaining EasySatSim/Python processes and then restart the program.

Do not run two main simulations at the same time if they use the same shared memory names.

## Result Export Reports `WinError 32`

Windows does not allow a file that is being used by another program to be overwritten.

If the target CSV is open in Excel, an editor, a preview pane, or a synchronization tool, close the related program and try again, or choose another export filename.

The export dialog suggests the following name by default:

```text
<result>_export.csv
```

If that file already exists, it continues with:

```text
_01
_02
...
```

If the selected destination path is the original result file itself, the interface does not copy the file again and instead reports that the result is already available at that location.

## A Notification in the Lower Right Is Difficult to Read

Notifications remain visible until they are manually closed. Multiple notifications stack upward, and long titles and file paths wrap automatically.

If notifications block the workspace, resize the main window if needed and close resolved notifications one by one.

`Run Log` preserves the same type of runtime context in a larger window.

## `No libpcap provider available`

In the IPv4 example, this warning means that Scapy cannot use libpcap for live packet capture.

This does not prevent the example from generating standard offline PCAP files.

You can open the following files directly in Wireshark:

```text
source_ipv4_udp.pcap
destination_ipv4_udp.pcap
```

## The IPv4 Example Does Not Look Like Standard IPv4

After the simulation finishes, run the result display program:

```powershell
python examples/protocol_ipv4_example/main.py
python examples/protocol_ipv4_example/show_result.py
```

Then inspect the generated PCAP files in Wireshark.

The default EasySatSim `DataPacket` is not a serialized standard IPv4 packet. Only the focused Scapy example replaces it with standard format IPv4/UDP packet bytes.

## A Long Simulation Takes Much Longer in Wall Time Than in Simulation Time

**Simulation time** and **wall time** are different.

Large constellations, more users, physical layer calculations, visualization, event logging, and machine learning training all increase wall time.

For paper experiments that require repeated execution, we recommend using the documented headless batch execution mode. The interactive interface is more suitable for scenario inspection and runtime observation.

Unless the change itself is part of the experiment definition, do not increase the simulation time step or disable the physical layer merely to accelerate a final experiment.

## Case 2 Cannot Download or Load CIFAR-10

First install:

```text
cases/case2/requirements.txt
```

For the first run, keep:

```python
CIFAR10_DOWNLOAD = True
```

torchvision stores the archive and extracted data under:

```text
cases/case2/experiment/data/
```

These files are local cache files and are ignored by Git.

If the data in this directory is incomplete or the directory is not writable, first preserve any required local copy, then correct the directory permissions or move the incomplete cache before running again.

Do not commit the downloaded dataset to the source repository.

The upstream download URL, checksums, offline checks, and dataset documentation are provided in:

```text
cases/case2/experiment/data/README.md
```

## Case 3 Batch Experiment Stops After One Run

The batch runner stops if any of the following occurs:

- metadata is missing;
- the generic network result file is missing;
- the event log is missing;
- the event log contains no usable packet generation or arrival events.

Check the partially generated batch manifest and the final console message. Fix the failed run before continuing the experiment.

Do not process an incomplete paired result as a complete comparative experiment.

## Only One Case 3 Routing Curve Appears

Reprocess the raw experimental results:

```powershell
python -m cases.case3.experiment.evaluation.process_results
```

Confirm that both modes exist for every random seed included in the statistics, and then redraw the figures:

```powershell
python -m cases.case3.plotting.plot_all_figures
```

The result processor deliberately excludes unpaired random seeds.

## Case 3 Failure or Route Refresh Occurs at the Wrong Time

Check whether the event log and metadata contain:

- failed satellite: `S377`;
- failure time: `105` seconds;
- centralized route deployment interval: `50` seconds;
- next failure aware route deployment time: `150` seconds.

Do not retune these parameters merely to make the event times visually align with changes in a curve.

If runtime execution is delayed, check whether the program correctly loads precomputed route tables instead of recalculating all routes online during execution.

## Case 3 Route Tables Are Missing or Incompatible

Regenerate the route tables only when the constellation size or failed satellite has been intentionally changed:

```powershell
python -m cases.case3.experiment.data.generate_centralized_route_tables
```

If only the random user seed is changed, the route tables do not need to be regenerated.

## Plotting Cannot Find Processed Data

Run the evaluation or result processing step for the case before running the plotting program.

For Case 3:

```powershell
python -m cases.case3.experiment.evaluation.process_results
python -m cases.case3.plotting.plot_all_figures
```

Also confirm that result cleanup has not removed raw log files that are still required by the result processor.

#