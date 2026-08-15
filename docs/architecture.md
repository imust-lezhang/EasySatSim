# Architecture

EasySatSim separates reusable simulation mechanisms from case specific research logic. A case usually creates the default scene first and then registers only the behaviors, protocols, routing, logging, or analysis functions required by that experiment.

## Runtime Flow

A typical EasySatSim runtime flow is shown below:

```text
configuration

SceneController
    EntityManager
        users, satellites, constellation, ground entity cluster
    BehaviorManager
        common behaviors, active behaviors, passive behaviors
    StackManager
        protocol data, protocol processing functions, protocol layer mappings
    routing callback
        next hop selection for network forwarding

configuration_complete()

Runtime stage
    entity process
        behaviors, buffers, protocol stack processing, performance statistics
    timer process
        simulation time and constellation state updates
    Qt interface
        3D/2D views, object information, performance metrics, logs, and result export
```

`SceneController` is the main entry point for scene construction and component composition. The normal initialization sequence is:

```python
scene = SceneController()
scene.create_scene()
scene.default_behavior()
scene.default_stack()

# Add case specific extensions here.

scene.configuration_complete()
scene.run_simulation(plotter=True)
```

Extensions should not be registered after `configuration_complete()`. Once this function is executed, the scene definition is considered complete.

## Configuration

The configuration module defines constellation geometry, user parameters, timing parameters, buffers, physical layer settings, and result output paths. The main simulator and each complete case can use separate configuration directories. The configuration loader activates the corresponding configuration directory before runtime modules are imported.

See the [Configuration Reference](configuration.md) for more details.

## Entities and Entity Clusters

The default scene contains individual entities and entity clusters:

- `User`: represents a ground user and maintains its access relationship, routing information, buffer, and protocol stack processing;
- `Satellite`: represents a satellite and maintains its orbital position, neighbor table, routing table, forwarding buffer, and protocol stack processing;
- `Constellation`: an entity cluster responsible for maintaining constellation wide position state;
- `Ground`: an entity cluster used to organize the ground user population.

`EntityManager` is responsible for creating and retrieving these objects. Extension code should use the interfaces provided by the manager rather than maintaining another entity registry that is incompatible with the existing mechanism.

## Behaviors

Behaviors describe the actions of entities or entity clusters during simulation:

- **common behaviors**: belong to entity clusters, such as updating the positions of all satellites in a constellation;
- **active behaviors**: are executed periodically by entities, such as user access to satellites, traffic generation, satellite neighbor announcements, or failure injection;
- **passive behaviors**: process input from buffers, such as protocol stack processing by satellites or users after data arrives.

A behavior must first be registered with `BehaviorManager` and then bound to the target entity or entity cluster through `EntityManager`. Registration alone does not cause the behavior to execute automatically.

## Protocol Stack

The EasySatSim protocol stack contains the application, transport, network, data link, and physical layers. For each layer, the manager maintains three categories of information:

1. protocol data types and their data conversion functions;
2. protocol identifiers and the corresponding parsing and encapsulation functions;
3. mappings that associate protocol identifiers with data types and processing functions.

The default protocol stack includes application ports, a compatible transport protocol, network protocols `0x0800` and `0x9000`, and data link and physical layer processing functions that use Ethernet naming conventions.

The default internal `DataPacket` is an EasySatSim data type and should not be described as a serialized standard IPv4 packet.

The Scapy example shows how standard IPv4/UDP packet bytes can be integrated through the same extension interfaces. See [Protocol Stack Extension](protocol_stack.md) for more details.

## Routing

Network forwarding obtains the next hop through the registered routing callback. The default callback uses minimum hop routing. A case can register another routing algorithm as follows:

```python
scene.register_routing_algorithm(MyRouting.routing_algorithm)
```

When the entity process starts, this callback is installed into the network layer protocol processing.

It is important to distinguish between **routing decision policy** and **packet processing policy**:

- if only next hop selection is changed, replacing the routing callback is usually sufficient;
- if route cache invalidation, route versions, TTL, or packet format must also be changed, additional or replacement network layer processing may be required.

Case 3 demonstrates both extension approaches. The distributed mode changes only the routing callback, while the centralized mode also replaces network layer processing to maintain global routing table versions.

## Physical Layer and Link Processing

Packets pass through entity buffers as well as link and physical layer processing.

When the physical layer model is enabled, the system uses current entity positions and the configured ISL or SGL parameters to calculate link state, transmission rate, propagation and processing delay, and loss conditions.

## Performance Metrics and Result Files

`NetworkPerformance` records network events during simulation and calculates network performance metrics from these events. Information such as packet transmission, arrival, and loss is used to calculate packet counts, delay, satellite load deviation, and other metrics. Some metrics are provided to the Dashboard through shared data for real time display, while network results are also saved to CSV files for further analysis after the simulation.

For the specific cases in the paper, the default network CSV generated by EasySatSim may not contain all the information required by an experiment. For example, the intrusion detection case may need to record attack and detection events, the machine learning case may need to record model training and aggregation processes, and the routing case may need to record routing changes. Therefore, each case can add independent event logs or other result files according to its experimental requirements.

In general, a complete experimental result processing workflow contains three stages:

- **Simulation and raw data recording**  
  Run EasySatSim and save the default network CSV, case specific event logs, and information such as the experiment configuration and random seed. These files form the raw experimental results.
- **Experimental metric calculation**  
  After the simulation ends, the evaluation program in the case directory reads the raw results, performs statistical processing and calculations according to the metrics defined in the paper, and generates processed metric files.
- **Result plotting**  
  The plotting program reads the calculated metric files and generates the figures used in the paper. Because plotting is independent of simulation execution, metrics can be recalculated or figures can be regenerated from saved raw results without rerunning the complete simulation.

We recommend keeping plotting separate from simulation execution. This allows figures to be regenerated from existing experimental results without rerunning a long simulation.

## Visualization

The Qt control window manages simulation state and worker processes. The Dashboard reads shared positions and performance metrics and provides 3D View, 2D View, Object Details, and performance charts.

The visualization module does not define the research experiment itself. Instead, it observes the configured simulation scene and provides operations for inspecting and exporting results.

See the [Visualization Guide](visualization.md) for more details.

## Cases and Examples

A complete case usually contains scenario configuration, experiment control, output validation, result evaluation, and plotting. A focused example is used to demonstrate a specific capability with less surrounding content.

Therefore:

- `cases/` is used for complete research scenarios corresponding to paper experiments;
- `examples/` is used for protocol or API examples;
- only reusable mechanisms that are genuinely general should be placed under `src/`.