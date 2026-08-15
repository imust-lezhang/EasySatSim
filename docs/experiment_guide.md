# Experiment Guide

This guide describes how to build a reproducible experimental workflow. The exact scenario definitions for each case remain specified in the corresponding `TUTORIAL.md`.

## 1. Separate the Experiment into Independent Stages

A workflow suitable for reproducing paper results should clearly separate the different stages:

1. **Define the experiment configuration and random seed**  
  Determine the constellation, users, traffic, failure events, algorithm mode, random seed, and other settings used in the experiment.
  
2. **Run the simulation and save raw results**  
  Run EasySatSim and save the raw network results, case event files, and metadata associated with the run.
  
3. **Calculate experimental metrics**  
  After the simulation ends, an independent result processing program reads the raw results, performs deterministic statistics and calculations according to the metrics defined in the paper, and generates processed data tables.
  
4. **Generate figures and values for the paper**  
  The plotting program reads the processed metric tables and generates PNG/PDF figures and the numerical values to be reported in the paper.
  

The plotting program should not silently rerun the simulation in the background. Changing a metric definition should also not overwrite existing raw experiment files.

## 2. What a Random Seed Controls

A random seed is used to initialize pseudorandom processes. Depending on the case, these random processes may include:

- random user locations;
- traffic generation times or payload selection;
- dataset partitioning or client sampling;
- machine learning model initialization and mini batch order;
- other explicit random processes using Python, NumPy, or other framework random number generators.

A random seed does not affect values that are fixed in the code, nor does it affect deterministic data loaded from fixed files.

For each case, the locations where randomness is used should be clearly recorded. If multiple random number libraries are used, all relevant random number generators should be initialized separately.

## 3. Paired Comparative Experiments

When comparing method A and method B, the same random seed should be used for both methods. For example:

```text
seed 1: A, B
seed 2: A, B
seed 3: A, B
...
```

This paired design allows the two methods to use comparable random users, traffic, and other random conditions.

For example, 10 paired seed groups require 20 simulation runs rather than 10.

Unless a setting is itself the experimental variable being compared, the following settings should remain identical:

- constellation and users;
- traffic;
- failures and their occurrence times;
- physical layer settings;
- time step and simulation duration;
- output file and event log formats;
- metric time windows and data inclusion rules.

## 4. Case 3 Batch Runner

Case 3 provides a complete example of paired experiment execution in the current repository.

To inspect the planned runs for 10 random seed groups without actually running the simulations, use:

```powershell
python cases/case3/run_experiment.py --seed-count 10 --dry-run
```

You can run between 1 and 20 paired seed groups, for example:

```powershell
python cases/case3/run_experiment.py --seed-count 3
python cases/case3/run_experiment.py --seed-count 10
```

For each random seed, the program runs both centralized and distributed modes, with only one headless simulation process running at a time.

After each run, the program checks the required output files and traffic events and generates a timestamped batch experiment manifest.

The batch runner is responsible only for executing simulations and checking outputs. It does not calculate result metrics or generate figures.

## 5. Raw Results and Metadata

Each simulation run should retain:

- the raw generic network CSV;
- the case event log;
- the actual random seed and method/mode used;
- a configuration snapshot or relevant parameter values;
- start and finish times;
- repository relative paths that associate the different result files;
- simulation completion status and result validation status.

Case 3 generates one metadata JSON file for each simulation and one manifest for the complete batch experiment.

If a batch experiment stops midway or only some runs are completed, the corresponding manifest should not be treated as a complete comparative experiment result.

## 6. Process Experimental Results

For Case 3, run:

```powershell
python -m cases.case3.experiment.evaluation.process_results
```

The result processing program:

- selects the newest complete centralized/distributed result pair for each random seed;
- checks whether the shared experiment settings of the two modes are comparable;
- matches packet generation events with arrival events;
- generates result tables aggregated by time window;
- generates summary tables for different experiment stages;
- generates a run manifest table.

In Case 3, the delivery ratio for a time window uses **packets generated within that time window** as the statistical population:

```text
delivery ratio = number of successfully delivered packets / total number of packets generated in the time window
undelivered ratio = 1 - delivery ratio
```

Average hop count is calculated only for packets that successfully reach the destination, because a lost packet does not have a complete end to end path.

Other cases use their own independent result processing programs. The metric definitions from Case 3 should not be applied directly to other cases. Follow the `TUTORIAL.md` for each case.

## 7. Generate Figures

For Case 3, run:

```powershell
python -m cases.case3.plotting.plot_all_figures
```

The plotting program reads the processed metric tables rather than the state of a running simulation.

Final figures are saved under:

```text
cases/case3/plotting/figures/
```

## 8. Experimental Workflows for Each Case

### Case 1

Case 1 separately performs IDS model training, fixed dataset evaluation, scenario simulation, scenario event evaluation, and plotting.

The main commands include:

```powershell
python -m cases.case1.experiment.ids.train_ids_deep_learning
python -m cases.case1.experiment.evaluation.evaluate_test_dataset
python cases/case1/main.py
python -m cases.case1.experiment.evaluation.evaluate_case_scenario_events
python cases/case1/plotting/plot_ids_detection_rates.py
python cases/case1/plotting/plot_packet_loss_rate.py
```

For the specific IDS modes and execution order, see:

`cases/case1/TUTORIAL.md`

### Case 2

Case 2 runs centralized learning and federated learning separately, then summarizes and plots the two sets of results:

```powershell
python cases/case2/main.py
python -m cases.case2.experiment.evaluation.summarize_case2_results
python -m cases.case2.plotting.plot_all_figures
```

For learning architecture switching, dependency installation, data preparation, and full simulation duration requirements, see:

`cases/case2/TUTORIAL.md`

## 10. Before Using Results in a Paper

Before using experimental results to generate figures or numerical values for a paper, confirm that:

- all planned simulations have completed;
- the raw results are not temporary outputs produced by lightweight validation or installation diagnostics;
- paired comparison methods use the same random seeds and shared experiment settings;
- metadata, file hashes, and file paths are internally consistent;
- the result processing program has read the expected number of runs and random seeds;
- if metric definitions have changed, figures have been regenerated using the latest metrics;
- the numerical values in the paper and the corresponding figures come from the same processed data table;
- software version, runtime environment, and hardware configuration have been recorded elsewhere.

If the experiment definition needs to be changed, archive the current raw results and related scripts before starting a new experiment.