# EasySatSim Test and Diagnostic Suite

This directory contains stepwise diagnostic programs for installation checks, visualization verification, and regression tests for core and integration functions. All tests use the independent small scale configuration under `tests/fixtures/small_config/` and write generated diagnostic artifacts only to `tests/artifacts/`.

## Why Stepwise Diagnostics Are Used

EasySatSim runtime and visualization involve multiple interrelated components. When the program does not run correctly, the problem may come from the Python environment, dependencies, EasySatSim configuration, Qt, VisPy, OpenGL, PyQtGraph, shared memory, or simulation processes. To make troubleshooting easier, the test suite divides the complete runtime process into several relatively independent diagnostic steps that check:

- Whether the Python environment and dependencies are correct;
- Whether the EasySatSim test configuration and resources can be loaded correctly;
- Whether the Qt application, event loop, window, and platform plugin work correctly;
- Whether VisPy can correctly use the PyQt5 backend;
- Whether the OpenGL context and graphics rendering work correctly;
- Whether PyQtGraph can continuously update data;
- Whether the EasySatSim Dashboard and its interface components can be constructed correctly;
- Whether satellite positions and performance metrics in shared memory can be refreshed in real time;
- Whether a short simulation can start, run, stop, and generate result files correctly.

Each diagnostic step runs in an independent Python process. This makes it easier to locate the source of a failure and prevents an abnormal state in one step from affecting later diagnostic steps.

## Important Dependency Note

EasySatSim currently uses **PyQt5**. The source code explicitly binds VisPy to the `pyqt5` backend, so PyQt6 cannot directly replace PyQt5 in the current visualization code.

The visualization library is named **VisPy** and is installed as `vispy`, not `Visby`.

From the project root, run the following command to install the dependencies required by the complete diagnostic and regression suite:

```powershell
python -m pip install -r tests/requirements-test.txt
```

This dependency file includes both the EasySatSim core dependencies and the dependencies required by the IPv4 example used in the integration tests.

## Run All Offscreen Diagnostics

From the repository root, run:

```powershell
python tests/run_all.py --mode offscreen
```

This mode is suitable for automated checks and systems without a visible desktop environment. It verifies window construction and rendering through the Qt offscreen platform. Passing the offscreen mode alone does not prove that a particular display driver or GPU works correctly in a normal desktop environment.

## Run Live Visualization Diagnostics

On a machine with a normal desktop session, run:

```powershell
python tests/run_all.py --mode live
```

`live` is the default mode. Therefore, running `tests/run_all.py` directly in PyCharm, or running the following command without arguments:

```powershell
python tests/run_all.py
```

will exercise the desktop Qt/OpenGL path and require Step 6 to pass. Automated CI environments and machines without a desktop environment must explicitly select `--mode offscreen`.

In live mode, several windows appear briefly and close automatically. Do not manually interact with or close these windows while a test step is running. This mode uses the Qt platform plugin and OpenGL display environment of the current system.

Live mode also serves as a release check. If any `FAIL` or `SKIP` occurs, the command exits with a nonzero status.

## Run Part of the Test Suite

You can start from a specified step, run only one step, or skip the integration tests:

```powershell
python tests/run_all.py --mode live --from-step 6
python tests/run_all.py --mode live --only-step 8
python tests/run_all.py --mode offscreen --skip-integration
```

The default timeout for each diagnostic step is 45 seconds and can also be adjusted manually:

```powershell
python tests/run_all.py --mode live --timeout 90
```

## Step Definitions and Passing Conditions

| Step | Test | Passing condition |
| --- | --- | --- |
| 0   | Environment | Records Python, operating system, system architecture, interpreter path, run mode, display related environment variables, and available Windows graphics adapter and driver information. |
| 1   | Dependencies | Required dependencies can be imported successfully; Qt runtime and platform plugins are recorded; the expected platform plugin exists; no other Qt binding is loaded. |
| 2   | Configuration | The independent test configuration loads correctly; derived configuration values are consistent; required resources exist; the test output directory is writable. |
| 3   | Qt application | `QApplication` starts successfully and its event loop can trigger a timer. |
| 4   | Qt window | A visible Qt window can be created and a nonempty screenshot can be saved. |
| 5   | VisPy backend | After explicit selection, VisPy reports the Qt/PyQt5 backend. |
| 6   | OpenGL Canvas | VisPy `SceneCanvas` can create an OpenGL context and render nonuniform pixels; the Qt platform, screen, OpenGL information, and rendered PNG are also recorded. |
| 7   | PyQtGraph | A curve can receive repeated data updates and a screenshot can be saved. |
| 8   | Dashboard | EasySatSim can create `3D View`, `2D View`, `Object Details`, `Performance Metrics`, and nine performance charts. |
| 9   | Control window | The initial Start/Stop state, menus, window before simulation, and persistent wrapped notification all work correctly. |
| 10  | Live refresh | Shared satellite positions and all performance charts receive repeated updates. |
| 11  | Short simulation | Independent timer and entity worker processes remain active; the Dashboard continues to refresh; worker processes stop correctly; and a valid CSV result is generated. |

## Regression Test Groups

After Step 11, `run_all.py` uses Python's standard library `unittest` framework to continue running core and integration regression tests. The current coverage includes:

- configuration derivation logic and preset schema;
- error handling for duplicate behavior registration and unknown behavior registration;
- default protocol stack mappings and isolation of local replacement;
- progress logic for minimum hop routing;
- physical layer configuration and discrete rate boundaries;
- average delay and hop metric calculations;
- export filename collision handling;
- Case 3 route table archive validation;
- IPv4 example protocol stack registration validation;
- Case 3 paired batch experiment dry run validation.

The two test groups can also be run directly:

```powershell
python -m unittest -v tests.unit.test_core
python -m unittest -v tests.integration.test_integrations
```

Test dependencies are defined in `tests/requirements-test.txt`. The current test suite itself uses `unittest`. `pytest` and `pytest-timeout` are also included in the test dependencies for later test development and CI extension.

## Generated Diagnostic Artifacts

Each complete run generates timestamped reports:

```text
tests/artifacts/diagnostics_<mode>_<timestamp>.json
tests/artifacts/diagnostics_<mode>_<timestamp>.md
```

Relevant steps also generate screenshots, and Step 11 generates a short diagnostic CSV. These files are automatically generated diagnostic artifacts and can be deleted before the next run.

## Interpreting Common Failures

- **Step 1**: dependencies may be missing, package names may be incorrect, or different Qt bindings may have been mixed.
- **Step 3/4**: usually related to the Qt platform plugin or the current display session.
- **Step 5**: VisPy selected a backend other than PyQt5.
- **Step 6**: usually related to OpenGL, the graphics driver, or a remote desktop environment.
- **Step 7**: may be related to PyQtGraph or Qt rendering.
- **Step 8**: may be related to EasySatSim resources, shared memory shapes, or Dashboard construction.
- **Step 9**: may be related to control window state or widget layout.
- **Step 10**: may be related to shared memory or periodic UI updates.
- **Step 11**: may be related to simulation process lifecycle, entity initialization, or result writing.

During troubleshooting, check the **first failed step** first. Later failures may only be consequences of the same underlying problem.
