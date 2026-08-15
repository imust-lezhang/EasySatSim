# Visualization Guide

The EasySatSim desktop interface separates simulation control, configuration management, result operations, and visual inspection. When the program starts, it first enters the state before simulation, allowing users to check the active configuration before worker processes are created.

The interface uses PyQt5, VisPy, and PyQtGraph. The 3D panel also requires a working desktop OpenGL environment. Before a release, or when running EasySatSim on a new machine for the first time, we recommend running:

```powershell
python tests/run_all.py --mode live --timeout 90
```

See the [Test Guide](../tests/README.md) for the passing criteria.

## Overview Before Simulation

The initial page displays:

- the number of orbital planes and satellites per plane;
- the total number of satellites;
- the number of users;
- the network time step;
- the physical layer state;
- the path of the active configuration file;
- the planned result file path.

Check these configuration items before starting a long simulation.

## Simulation Menu

| Action | Function |
| --- | --- |
| `Start Simulation` | Validates the current configuration, assigns a timestamped path to the result file, and starts the timer and entity worker processes. |
| `Stop Simulation` | Terminates the simulation worker processes and waits for the related processes to exit. |
| `Run Log` | Opens the persistent run log window for viewing initialization, runtime status, result output, and error information. |

Actions that are unavailable in the current state are disabled and displayed in gray.

The configuration cannot be edited after the simulation starts.

## Configuration Menu

`Edit Configuration` is used to edit the active main configuration fields as Python expressions. The program performs syntax and runtime validation when the configuration is saved.

`Configuration Presets` provides built in constellation presets, selection of `simulation_config*.py` configuration files, and saving of the current configuration.

When a custom configuration is saved, the entered name is normalized and the file is stored under `configuration/` in the following form:

```text
simulation_config.<name>.py
```

Before changing parameters or configuration items that may affect experimental results, we recommend reading the [Configuration Reference](configuration.md).

## Results Menu

| Action | Function |
| --- | --- |
| `Export Result` | Copies the generated CSV file to a location selected by the user. The default export filename adds `_export` and avoids overwriting a file with the same name. |
| `Package Run` | Creates a ZIP file containing the experimental result, configuration file, screenshot, run log, and text manifest. |
| `Open Output Folder` | Opens the directory containing the current result file. |
| `Save Screenshot` | Saves the current application window as an image. |

If the target export file is open in Excel or another program, Windows may lock the file. EasySatSim reports this through a notification. In this case, close the program that is using the file or choose a new export filename.

## View Menu

The `View` menu is used to reopen different panels and control their arrangement, including:

- `3D View`;
- `Object Details`;
- `2D View`;
- `Performance Metrics`;
- the performance metric window for the most recent 60 seconds;
- tiled or cascaded panel layouts.

These view operations become available after the Dashboard has been created.

## 3D View

The 3D panel uses shared simulation state to display the Earth, satellite constellation, users, access links, routing paths, and related information.

This view is mainly used to inspect spatial relationships and satellite movement.

## 2D View

The 2D panel displays the longitude and latitude projection of satellites and users.

This view can be used to inspect satellite ground tracks and approximate access relationships between users and satellites.

The 2D and 3D panels observe the same running simulation scene.

## Object Details

`Object Details` contains two types of information: a scene overview and details of the selected object.

Before the simulation starts, the overview page displays information about the currently configured scene.

During simulation, a satellite or user can be selected in the 2D panel according to its object type and identifier, and the currently available runtime properties of that object can then be inspected.

## Performance Metrics

The performance metrics panel displays real time metrics from shared runtime statistics.

These charts are mainly used to observe simulation runtime status. Final experimental results for the paper should be calculated from the saved raw result files and event files using the evaluation programs provided in the corresponding cases.

For charts that support this function, `Show Recent 60 Seconds` limits the displayed window to the most recent 60 seconds without changing the saved experimental data.

## Status Area

The status area at the bottom of the interface displays the current runtime state, elapsed wall time, result summary, and related information.

**Simulation time** and **wall time** should be distinguished. Because computational load may vary, the same duration of simulation time may require different amounts of wall time.

## Notifications

Status and error information is displayed as notification cards in the lower right corner of the interface.

Each notification records its creation time and remains visible until it is manually closed. Multiple notifications are arranged upward in sequence.

## Run Log

`Run Log` stores more detailed runtime information than ordinary notifications.

## Headless Runs

The default scene can run without starting the Dashboard by using:

```python
run_simulation(plotter=False, ...)
```

The Case 3 batch experiment program also provides a documented headless execution mode.

Headless mode is more suitable for repeatedly running a large number of experiments, while the interactive interface is more suitable for inspecting scenario configuration, runtime status, and visualization results.