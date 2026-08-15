# Development Guide

This guide describes the extension approaches currently supported by EasySatSim and the verification methods appropriate for changes of different scales. We recommend reading the [Architecture](architecture.md) first.

## Repository Directory Responsibilities

```text
src/             reusable simulation mechanisms
configuration/   main simulator configuration and presets
cases/           complete research scenarios and paper experiment workflows
examples/        focused API or protocol examples
tests/           automated tests
resource/        runtime maps, population data, and image resources
docs/            user and developer documentation
output/          main simulator runtime results
```

Code should be placed in `src/` only when it can be reused across multiple scenarios and does not depend on assumptions specific to a particular case.

## Create a New Case

The recommended directory structure is:

```text
cases/my_case/
  main.py
  case_setup.py
  src/
    configuration/
    entity/
    behaviors/
    stack/
  experiment/
    data/
    integration/
    evaluation/
    output/
  plotting/
    figures/
```

A case entry program should usually perform the following steps:

1. add the project root and case root to the import path in the documented order;
2. load the case configuration;
3. create the default scene, default behaviors, and default protocol stack;
4. call the case specific setup function;
5. complete the scene configuration and start the simulation.

Overrides passed through the command line should affect only the current process, and we recommend recording these parameters in the run metadata.

## Entity Extension

Entities and entity clusters should be managed through `EntityManager`.

If the existing `User` and `Satellite` types already satisfy the requirements, their functionality should preferably be extended through configuration and binding mechanisms.

If a new reusable entity type is required, it should implement the corresponding abstract interfaces under `src/abstract/`.

## Behavior Extension

Behavior extension follows the principle of registering first and binding second:

```python
behavior_manager.add_active_behavior(
    behavior_name="my_behavior",
    behavior_func=MyBehavior.run,
    interval=1.0,
    is_async=True,
    data=None,
    last_run=None,
)

entity_manager.bind_active_behavior(
    behavior_manager=behavior_manager,
    entity=user,
    behavior_name="my_behavior",
)
```

For periodic operations across an entity cluster, use `add_common_behavior()`.

For processing triggered by events or queues, use `add_passive_behavior()`.

Each behavior should use a unique and descriptive name, and its execution interval and binding relationship should be verified. A behavior that has been registered but not bound to a target entity or entity cluster will not execute.

## Protocol Extension

Protocol extensions should use the public interfaces provided by `StackManager`:

- `add_protocol_data()`;
- `add_protocol_func()`;
- `add_relationship()`;
- `replace_protocol_func()`;
- `replace_relationship()`;
- use `register_routing_algorithm()` through `SceneController`.

Do not modify the manager's internal dictionaries directly.

See [Protocol Stack Extension](protocol_stack.md) for specific examples and verification methods.

## Routing Extension

A reusable routing callback should clearly define its input and output formats and use deterministic selection for equivalent paths.

At a minimum, we recommend verifying the following situations:

- the source node is the same as the destination node;
- the destination node does not exist;
- a neighbor is unavailable or its information is stale;
- loop avoidance;
- no route is available;
- route cache refresh or invalidation;
- deterministic selection among equal cost paths.

If an experiment changes not only next hop selection but also route table versions or packet fields, the network layer logic should be explicitly extended rather than hiding these state changes inside the routing callback.

## Performance Metrics and Logging

For general network performance, the generic network metrics provided by EasySatSim can be used directly.

When experimental evaluation requires additional metrics to be recorded, add a case specific event log.

The event log schema should remain stable and contain enough information to allow the corresponding metrics to be reconstructed independently after the simulation.

We also recommend recording metadata that associates:

- event logs;
- network result files;
- configuration;
- random seed;
- experiment mode;
- timestamps.

Raw outputs should be treated as fixed inputs to subsequent evaluation. Result processing and plotting can be repeated, and a complete simulation should not need to be rerun merely to change figure styling.

## Configuration Changes

Within the same configuration directory, keep:

```text
simulation_config.py
simulation_config.default.py
```

consistent in configuration structure.

Presets for the main program must preserve the same uppercase field set and field order as the default configuration.

Case configuration files may add fields used only by that case.

For derived parameters that can be calculated from existing fields, we recommend keeping them as expressions where practical. For example:

```python
TOTAL_SATELLITE_NUMBER = ORBIT_NUMBER * SATELLITE_NUMBER_PRE_ORBIT
```

## Layered Verification Workflow

Start with the smallest verification that can reveal a problem, then gradually expand the verification scope.

### 1. Syntax and Import Checks

```powershell
python -m compileall -q src configuration cases examples
```

### 2. Unit or Static Checks

Without starting worker processes, independently verify a manager registration process, configuration derivation, route table loader, or pure result evaluation function.

### 3. Short Deterministic Integration Check

Use a small scale scene or the IPv4 example to verify processing across multiple protocol layers, multi hop forwarding, and the corresponding output evidence.

### 4. Single Mode Scenario Check

Select one method and one random seed, and run long enough to cover all important event boundaries.

Check whether output file headers, event types, and metadata are correct.

### 5. Paired or Batch Check

First use a dry run command to inspect the planned execution, then run one paired seed group. After confirming that it works correctly, run the complete batch.

### 6. Full Experiment

Run the full experiment only after the previous checks pass.

The raw results and manifest from the full experiment should be retained.

The repository's `tests/` directory is used for automated regression tests.

If a component affected by a change is not covered by existing tests, add a focused test or clearly record a specific command that can deterministically verify the change.

#