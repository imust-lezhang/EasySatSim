# Routing Extension Example

## Purpose

This directory provides a minimal example of the EasySatSim routing extension interface, corresponding to the routing extension example shown in Figure 3(c) of the manuscript.

This example focuses only on the form of a custom routing callback. It is not a standalone simulation scenario and does not include configuration files, an executable entry point, traffic definitions, evaluation programs, or experiment results.

For a complete and reproducible routing experiment, see [Case 3](../../cases/case3/TUTORIAL.md).

## Routing Callback Interface

A custom routing algorithm should inherit from `RoutingAlgorithm` and implement the following static method:

```python
@staticmethod
def routing_algorithm(
    entity,
    cross_layer_message,
    src_satellite_id,
    dst_satellite_id,
):
    ...
    return next_satellite_id
```

The callback receives:

- `entity`: the satellite currently making the forwarding decision;
- `cross_layer_message`: the message currently being processed by the protocol stack;
- `src_satellite_id`: the current source satellite identifier used for routing calculation;
- `dst_satellite_id`: the identifier of the satellite accessed by the destination user.

The function returns the identifier of the next hop satellite. When making a routing decision, the callback may use topology, neighbor status, link state, delay, load, routing table information, or other scene specific data.

The file [`routing.py`](routing.py) shows the required class and method form. It provides a compact interface example, but it is not a complete experiment that can be run directly.

## Registering a Routing Algorithm

During scene setup, register the routing callback before starting the simulation:

```python
from examples.routing_example.routing import CustomRoutingAlgorithm

scene_controller.register_routing_algorithm(
    CustomRoutingAlgorithm.routing_algorithm
)
```

EasySatSim then installs this callback as the next hop routing function used by the default network layer processing. The custom callback selects the next hop satellite, while EasySatSim continues to provide its default functions.

## Complete Reference: Case 3

Case 3 shows how to use the routing extension interface in a complete satellite network experiment. It compares two routing strategies under the same permanent satellite failure scenario:

- centralized periodic routing based on globally deployed route tables;
- distributed local rerouting that bypasses an unavailable next hop.

The relevant files are:

| Purpose | File |
| --- | --- |
| Complete tutorial and reproduction workflow | [`cases/case3/TUTORIAL.md`](../../cases/case3/TUTORIAL.md) |
| Scene setup and routing registration | [`cases/case3/case_setup.py`](../../cases/case3/case_setup.py) |
| Centralized routing callback | [`centralized_routing.py`](../../cases/case3/experiment/routing/centralized_routing.py) |
| Distributed routing callback | [`distributed_rerouting.py`](../../cases/case3/experiment/routing/distributed_rerouting.py) |

If you only need the routing interface, this directory can be used as a short reference. If you need a runnable scenario, follow the Case 3 tutorial.