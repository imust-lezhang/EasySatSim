# Case 3 Tutorial: Routing Comparison in Satellite Networks

This tutorial explains how Case 3 is built on top of EasySatSim. It is written
for readers who want to understand how to add a new case study, not only how to
run the finished scripts.

The tutorial follows the actual implementation order of the case. Each step introduces a small group of files, explains how they connect to EasySatSim, and provides a verification method before the final long running experiment.

Run all commands from the EasySatSim project root.

## Prerequisites

Install the complete Case 3 environment with:

```powershell
python -m pip install -r cases/case3/requirements.txt
```

The Case 3 simulation uses the EasySatSim core dependencies. Its result
processor additionally uses pandas, and its two figure scripts use Matplotlib;
the case requirements file installs the full simulation to figure pipeline.

## 1. Tutorial Goal

The goal of Case 3 is to compare centralized routing and distributed routing under one permanent satellite failure without modifying the EasySatSim core.

The final scenario contains:

- A Quarter Starlink constellation with 16 orbits and 25 satellites per orbit, for 400 satellites in total.
- 200 users divided into two regional groups with 100 users each.
- Reproducible random user coordinates sampled around eight fixed regional
  subcenters.
- 100 bidirectional user pairs that generate controlled traffic through
  application port 18080.
- Permanent failure of satellite 377 at 105 seconds.
- Centralized routing that deploys a global route table version every 50
  seconds.
- Distributed routing that normally reuses EasySatSim's minimum hop routing and
  performs a local bypass when the default next hop is unavailable.
- Event logs that record packet generation, packet arrival, path length, hop
  count, and satellite failure.
- A paired seed batch runner for 1-20 seed groups.
- Evaluation code for packet undelivered ratio and average hop count.
- Plotting scripts that generate the two figures used by the paper.

The comparison focuses on the interval between the failure at 105 seconds and
the next centralized deployment at 150 seconds. During this interval, the
centralized method still uses the route table version deployed at 100 seconds,
whereas the distributed method can bypass the failed next hop locally.

### How to Use This Tutorial

This document supports two reading paths:

- To reproduce the finished experiment, install the prerequisites and follow
  Sections 17-19. The implementation steps can be read later when a component
  needs to be understood or modified.
- To understand how a routing case is added to EasySatSim, follow Sections 3-16 in order. Each step identifies the extension point, explains the important logic, and provides a verification command.

The implementation code blocks are focused excerpts. They explain the routing
and event flow without duplicating every import, validation branch, or helper.
The complete executable implementation is the source file identified by each
step and by the following map.

### EasySatSim Extension Map

| Layer | Case 3 addition | Complete implementation |
| --- | --- | --- |
| Entry and scene wiring | Select mode/seed and connect all Case 3 extensions | [`main.py`](main.py), [`case_setup.py`](case_setup.py) |
| Batch execution | Run paired centralized/distributed seeds and validate raw outputs | [`run_experiment.py`](run_experiment.py) |
| Configuration | Quarter-Starlink scene, users, traffic, failure, routing, physical layer, and outputs | [`src/configuration/simulation_config.py`](src/configuration/simulation_config.py) |
| User deployment | Seeded regional coordinates and bidirectional pairing | [`experiment/data/user_groups.py`](experiment/data/user_groups.py) |
| Active behavior | Controlled pair traffic and permanent satellite failure | [`src/behaviors/`](src/behaviors/) |
| Protocol stack | Port 18080 processing and centralized network layer version handling | [`src/stack/`](src/stack/) |
| Centralized routing | Precomputed tables, control center deployment, and routing callback | [`experiment/data/`](experiment/data/), [`experiment/routing/centralized_control.py`](experiment/routing/centralized_control.py), [`experiment/routing/centralized_routing.py`](experiment/routing/centralized_routing.py) |
| Distributed routing | Default minimum hop routing with local failure bypass | [`experiment/routing/distributed_rerouting.py`](experiment/routing/distributed_rerouting.py) |
| Experiment records | Traffic/failure events, portable paths, and run metadata | [`experiment/integration/`](experiment/integration/) |
| Evaluation | Pair runs and calculate time bin and phase metrics | [`experiment/evaluation/process_results.py`](experiment/evaluation/process_results.py) |
| Plotting | Generate undelivered ratio and average hop count figures | [`plotting/`](plotting/) |

### Routing and Event Flow

Centralized routing and distributed routing differ only in how they respond after the failure occurs. In both modes, users send controlled bidirectional traffic through application port `18080`. After a packet enters the access satellite, the routing callback for the current mode selects the next hop, and the packet is forwarded hop by hop through the satellite network until it reaches the destination user. Case 3 separately records packet generation and successful arrival events, together with information such as message ID, path, hop count, and delay, for later calculation of undelivered ratio and average hop count.

In **centralized routing mode**, the system deploys precomputed global routing tables at 0, 50, 100, and 150 seconds. After satellite 377 permanently fails at 105 seconds, the system continues to use the routing table deployed at 100 seconds. Therefore, during the 105 to 150 second interval, that table does not yet reflect the failure of satellite 377. At 150 seconds, the system deploys a new failure aware routing table, allowing centralized routing to avoid satellite 377 again.

In **distributed routing mode**, satellites normally use the EasySatSim default minimum hop routing result. If the default next hop is still alive and available, forwarding continues along the original path. If the default next hop has failed, the current satellite uses local neighbor information to choose an unvisited and still available neighbor as a local bypass next hop, allowing packet forwarding to continue without waiting for a global routing table update.

Therefore, the 105 to 150 second interval is the main comparison window in this case. During this period, both modes face the same satellite 377 failure, but centralized routing remains affected by the old routing table while distributed routing can immediately perform local bypass. The performance difference in this interval mainly reflects the difference between the two routing response mechanisms.

## 2. Final Directory Structure

The finished case is organized as follows:

```text
cases/case3/
  main.py
  run_experiment.py
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
      controlled_pair_traffic.py
      satellite_failure_behavior.py
      __init__.py
    stack/
      application_layer.py
      network_layer.py
      __init__.py
    __init__.py

  experiment/
    data/
      user_groups.py
      centralized_route_tables.py
      generate_centralized_route_tables.py
      centralized_route_tables.npz
      __init__.py
    routing/
      centralized_control.py
      centralized_routing.py
      distributed_rerouting.py
      __init__.py
    integration/
      event_logger.py
      paths.py
      run_metadata.py
      __init__.py
    evaluation/
      process_results.py
      __init__.py
    output/
      *.csv
      *.json
      *.md
    __init__.py

  plotting/
    _common.py
    plot_undelivered_ratio.py
    plot_average_hop_count.py
    plot_all_figures.py
    figures/
      CASE3_UNDELIVERED_RATIO.png
      CASE3_AVERAGE_HOP_COUNT.png
    __init__.py
```

The directories have different roles:

```text
src/
```

Contains the code that is directly connected to the EasySatSim simulation:
case local configuration, active behaviors, and protocol stack extensions.

```text
experiment/
```

Contains the experiment definition and analysis materials: user grouping, precomputed route tables, routing strategies, event logging, run data, evaluation code, and outputs.

```text
plotting/
```

Contains only the common plotting style, the two figure scripts, and generated
PNG files.

The separation follows the same principle as the other EasySatSim tutorials:

```text
src/          how the case extends the simulator
experiment/   what the case evaluates
plotting/     how the paper figures are generated
```

## 3. Step 1: Create the Case Entry and Configuration

### Goal

Create an isolated Case 3 entry point that reuses the EasySatSim source tree but
loads its own configuration from `cases/case3/src/configuration/`.

This allows Case 3 to define its own parameters without changing the global configuration used by other cases.

### Files to Add

Create:

```text
cases/case3/
  main.py
  case_setup.py
  src/
    configuration/
      simulation_config.py
      simulation_config.default.py
      __init__.py
    __init__.py
```

### Define the Case Configuration

The active configuration file is:

```text
cases/case3/src/configuration/simulation_config.py
```

The two values normally changed for a single manual run are:

```python
CASE3_ROUTING_MODE = "centralized"  # "centralized" or "distributed"
CASE3_RANDOM_SEED = 20260811
```

The batch runner overrides them through environment variables, so it does not
need to rewrite the configuration file:

```python
CASE3_ROUTING_MODE = os.environ.get(
    "EASYSATSIM_CASE3_ROUTING_MODE", CASE3_ROUTING_MODE
).strip().lower()

CASE3_RANDOM_SEED = int(
    os.environ.get("EASYSATSIM_CASE3_RANDOM_SEED", CASE3_RANDOM_SEED)
)
```

The output timestamp is generated once by the parent process and inherited by
Windows multiprocessing children:

```python
CASE3_OUTPUT_TIMESTAMP = os.environ.get(
    "EASYSATSIM_CASE3_OUTPUT_TIMESTAMP",
    datetime.now().strftime("%Y%m%d_%H%M%S"),
)
```

This prevents the event writer, network writer, and metadata writer from using different file names when a child process starts later.

### Fixed Experiment Parameters

The central configuration values are:

```python
ORBIT_NUMBER = 16
SATELLITE_NUMBER_PRE_ORBIT = 25
ORBIT_INCLINATION = 53
ORBIT_HEIGHT = 1150

USER_NUMBER = 200
CASE3_PAIR_COUNT = 100
CASE3_APPLICATION_PORT = 18080
CASE3_TRAFFIC_START_TIME = 5.0
CASE3_CONTROLLED_SEND_PERIOD = 2.0
CASE3_CONTROLLED_PACKET_SIZE_BYTE = 1200

CASE_SIMULATION_END_TIME = 200
CASE3_FAILED_SATELLITE_ID = 377
CASE3_FAILURE_TIME = 105.0
CASE3_CENTRALIZED_ROUTE_REFRESH_INTERVAL = 50.0
```

The output names include mode, seed, and timestamp:

```python
CASE3_OUTPUT_PREFIX = f"{CASE3_ROUTING_MODE}_seed_{CASE3_RANDOM_SEED}"

SAVE_FILE_PATH = (
    "../cases/case3/experiment/output/"
    f"easysatsim_result_{CASE3_OUTPUT_PREFIX}_{CASE3_OUTPUT_TIMESTAMP}.csv"
)

CASE3_EVENT_LOG_FILE_PATH = (
    "cases/case3/experiment/output/"
    f"case3_events_{CASE3_OUTPUT_PREFIX}_{CASE3_OUTPUT_TIMESTAMP}.csv"
)
```

### Write the Entry Point

`main.py` first places the project root at the front of `sys.path`, then loads
the Case 3 configuration before importing `configuration.simulation_config`:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.config_loader import load_configuration
load_configuration("cases/case3/src")
```

The scene construction order is:

```python
scene_controller = SceneController()
scene_controller.create_scene()
scene_controller.default_behavior()
scene_controller.default_stack()
configure_case3_scene(scene_controller)
scene_controller.configuration_complete()
scene_controller.run_simulation(...)
```

This order is important. Case 3 first loads EasySatSim's default entities,
behaviors, and stack, then replaces or extends only the components required by
the experiment.

### Verify This Step

Run:

```powershell
python -c "from cases.case3 import main; print(main.cg.TOTAL_SATELLITE_NUMBER, main.cg.USER_NUMBER, main.cg.CASE3_FAILED_SATELLITE_ID)"
```

Expected output:

```text
400 200 377
```

Compile the case:

```powershell
python -m compileall -q cases\case3
```

## 4. Step 2: Add Reproducible User Groups and Pairing

### Goal

Create two regional user groups that vary across seeds while remaining
identical between centralized and distributed routing for the same seed.

This avoids two undesirable extremes:

- completely fixed coordinates that provide no across seed spatial variation;
- unrelated random coordinates that make the two routing modes incomparable.

### File to Add

Create:

```text
cases/case3/experiment/data/user_groups.py
```

### Define the Regional Subcenters

Group A uses four subcenters:

```python
GROUP_A_SUBCENTERS = (
    (33.6, -7.4),
    (36.0, -3.6),
    (38.2, -6.0),
    (34.7, -1.6),
)
```

Group B uses four subcenters:

```python
GROUP_B_SUBCENTERS = (
    (32.8, 111.5),
    (35.7, 116.8),
    (38.5, 113.6),
    (34.4, 120.2),
)
```

Each user is sampled uniformly inside a one degree disk around one subcenter:

```python
COORDINATE_MODEL = "seeded_uniform_disks"
CLUSTER_RADIUS_DEG = 1.0
```

Using `sqrt(U)` for the radius creates a spatially uniform disk.

### Build Reproducible Coordinates

The coordinate generator uses only the configured Case 3 seed:

```python
rng = np.random.default_rng(cg.CASE3_RANDOM_SEED)
```

It creates 100 Group A locations and 100 Group B locations, then returns them
in user id order:

```text
users 0-99     Group A
users 100-199  Group B
```

For a given seed, repeated calls return identical coordinates. Changing the
seed produces a different deployment under the same eight subcenter model.

### Define Bidirectional Pairs

The pair relation is deterministic:

```text
user i       <-> user 100 + i
pair id i        for i = 0 ... 99
```

`get_pair_for_user(user_id)` returns:

```python
{
    "pair_id": pair_id,
    "target_user_id": target_user_id,
    "direction": "A_to_B" or "B_to_A",
}
```

Thus 100 pairs generate traffic in both directions.

### Assign Locations to EasySatSim Users

`case_setup.py` calls `build_case3_user_locations()` and applies each coordinate
through the existing entity interface:

```python
user.set_position(latitude=latitude, longtitude=longitude)
```

No new user entity type is required.

### Verify This Step

Run:

```powershell
python -c "from cases.case3 import main; from cases.case3.experiment.data.user_groups import build_case3_user_locations, get_pair_for_user; a=build_case3_user_locations(); b=build_case3_user_locations(); print(len(a), a==b, get_pair_for_user(0), get_pair_for_user(100))"
```

Expected properties:

```text
200 coordinates
the two coordinate lists are equal
user 0 targets user 100
user 100 targets user 0
```

## 5. Step 3: Add Controlled Pair Traffic

### Goal

Replace EasySatSim's default random user traffic with reproducible,
bidirectional pair traffic.

The routing comparison should use the same offered traffic in both modes.
Leaving the default random sender active would make packet timing and
destinations difficult to match across runs.

### File to Add

Create:

```text
cases/case3/src/behaviors/controlled_pair_traffic.py
```

### Implement the Active Behavior

The behavior class is:

```python
class ControlledPairTraffic(AbstractBehavior):
    @staticmethod
    async def send_case3_pair_data(entity, data):
        ...
```

For each user, it:

1. resolves the paired destination;
2. waits until the user's next scheduled send time;
3. verifies satellite access and stack state;
4. creates a unique message id;
5. encapsulates a `DataMessage` through port 18080;
6. places the message in the access satellite buffer;
7. records packet generation in EasySatSim performance counters;
8. appends a `generate` row to the Case 3 event log.

Message ids follow this form:

```text
case3-<source-user id>-<target-user id>-<sequence-number>
```

They are later used to match generated packets with their first successful arrival.

### Stagger the First Transmission

All users use a two second send period, but their first transmissions are
spread across 50 slots:

```python
offset = (
    entity.entity_id % CASE3_CONTROLLED_STAGGER_SLOT_COUNT
) * CASE3_CONTROLLED_SEND_PERIOD / CASE3_CONTROLLED_STAGGER_SLOT_COUNT
```

This avoids an artificial burst in which all 200 users transmit at exactly the
same instant.

### Register and Bind the Behavior

`case_setup.py` registers the active behavior under:

```text
case3_controlled_pair_send
```

It then removes the default sender from every user:

```python
user.get_active_behaviors().pop("simple_send_data", None)
```

The normal EasySatSim satellite access behavior remains active. Only random
traffic generation is replaced.

### Verify This Step

Run:

```powershell
python -c "from cases.case3.case_setup import CASE3_TRAFFIC_BEHAVIOR_NAME; from cases.case3.src.behaviors.controlled_pair_traffic import ControlledPairTraffic; print(CASE3_TRAFFIC_BEHAVIOR_NAME, ControlledPairTraffic.__name__)"
```

Expected output includes:

```text
case3_controlled_pair_send ControlledPairTraffic
```

## 6. Step 4: Add the Case 3 Application Layer Port

### Goal

Add an application layer service that receives controlled pair messages and
records delivery and route information.

### File to Add

Create:

```text
cases/case3/src/stack/application_layer.py
```

### Define the Protocol Function

The protocol function is:

```python
class Case3ControlledTrafficPort(AbstractProtocolFunc):
    ...
```

Its encapsulation function forwards the message to transport protocol
`0x0006`:

```python
cross_layer_message.cross_layer_interface = 0x0006
```

Its parsing function runs when a Case 3 message reaches the destination user.
It:

- parses the Case 3 payload fields;
- calls `NetworkPerformance.packet_arrive(...)`;
- calculates satellite hop count from the stored path;
- converts the stored IP path into satellite ids;
- appends an `arrival` event;
- stops further stack processing.

The hop count is calculated as:

```python
hop_count = max(len(path) - 2, 0)
```

The two user endpoints are removed from the stored path length, leaving the
satellite forwarding hops used by the experiment.

### Register Port 18080

`case_setup.py` adds the application protocol function:

```python
stack_manager.add_protocol_func(
    layer_name="application",
    protocol_name=18080,
    parse_func=Case3ControlledTrafficPort.parse_and_process_func,
    encapsulate_func=Case3ControlledTrafficPort.encapsulate_func,
)
```

It then connects the protocol function to EasySatSim's existing
`DataMessage` type:

```python
stack_manager.add_relationship(
    layer_name="application",
    protocol_name=18080,
    data_name="data_message",
)
```

No new transport, link, or physical protocol is required.

### Verify This Step

Compile the stack extension:

```powershell
python -m compileall -q cases\case3\src\stack
```

## 7. Step 5: Add Event Logging and Run Metadata

### Goal

Record enough information to calculate metrics from actual packet events and to
verify that paired runs use comparable experiment settings.

### Files to Add

Create:

```text
cases/case3/experiment/integration/
  event_logger.py
  paths.py
  run_metadata.py
```

### Event Log

`event_logger.py` writes these fields:

```text
event_type
simulation_time
message_id
pair_id
direction
source_user_id
target_user_id
source_access_satellite_id
target_access_satellite_id
delay_ms
hop_count
path_length
path_satellite_ids
note
```

The current event types are:

```text
generate
arrival
satellite_failure
```

The log is initialized before simulation and protected by a thread lock while
rows are appended.

### Run Metadata

After one simulation finishes, `run_metadata.py` writes a JSON file containing:

- routing mode and random seed;
- output timestamp;
- duration, failure satellite, and failure time;
- centralized deployment interval and route table sequence;
- project relative event log and network log paths;
- constellation parameters;
- user model, subcenters, coordinate seed, and coordinate hash;
- physical layer settings.

The coordinate hash is especially important. The evaluation script checks that
centralized and distributed runs with the same seed used the same user
coordinates.

### Verify This Step

Compile the integration package:

```powershell
python -m compileall -q cases\case3\experiment\integration
```

## 8. Step 6: Add Permanent Satellite Failure

### Goal

Inject one permanent satellite failure at a controlled simulation time without
changing EasySatSim's core entity classes.

### File to Add

Create:

```text
cases/case3/src/behaviors/satellite_failure_behavior.py
```

### Implement the Failure Behavior

The behavior checks the simulation clock and calls:

```python
target_satellite.set_dead()
```

when the clock reaches:

```text
105 seconds
```

The target is:

```text
Satellite 377
```

`set_dead()` updates the satellite's survival state, marks its shared metrics as
unavailable, and disconnects attached users. The Case 3 behavior also writes a
`satellite_failure` event.

There is no recovery event in this scenario.

### Register the Active Behavior

The registered behavior name is:

```text
case3_satellite_failure_once
```

`case_setup.py` passes the satellite 377 object as the behavior data. The behavior is bound to user schedulers as a lightweight carrier for checking the global event condition, but the failure target remains satellite 377 and the users do not fail. The behavior contains a one time guard so that only the first scheduler that reaches the condition changes the satellite state.

### Verify This Step

Run:

```powershell
python -c "from cases.case3 import main; from cases.case3.case_setup import CASE3_FAILURE_BEHAVIOR_NAME; print(CASE3_FAILURE_BEHAVIOR_NAME, main.cg.CASE3_FAILED_SATELLITE_ID, main.cg.CASE3_FAILURE_TIME)"
```

Expected output:

```text
case3_satellite_failure_once 377 105.0
```

## 9. Step 7: Precompute the Centralized Route Tables

### Goal

Prepare the centralized route information offline so that global route
calculation does not block the simulation event loop.

The initial implementation calculated all 400-by-400 source to destination routes
during each online refresh. That synchronous computation paused user behavior
execution and delayed both traffic and failure injection. Case 3 therefore
stores the two topology states required by this fixed tutorial scenario.

### Files to Add

Create:

```text
cases/case3/experiment/data/
  centralized_route_tables.py
  generate_centralized_route_tables.py
  centralized_route_tables.npz
```

### Define the Two Unique States

The archive contains two `400 x 400` integer matrices:

```text
normal       all 400 satellites available
s377_failed S377 excluded from all routes
```

Each matrix entry is:

```text
table[source_satellite_id, destination_satellite_id] = next_hop_satellite_id
```

`-1` means that no route is defined.

The normal table follows the EasySatSim default minimum hop direction logic.
The `s377_failed` table uses breadth first search on the satellite network with satellite 377 excluded from the neighbor graph.

### Define the Four Deployments

Only two matrices are unique, but the controller performs four deployments:

```text
0 seconds    normal
50 seconds   normal
100 seconds  normal
150 seconds  s377_failed
```

This preserves the intended stale route interval:

```text
105-150 seconds
```

Satellite 377 fails at 105 seconds, but centralized routing does not deploy the failure aware table until 150 seconds.

### Generate the Archive

The repository already contains the matching archive. Regenerate it only if
the constellation dimensions or failed satellite are deliberately changed:

```powershell
python -m cases.case3.experiment.data.generate_centralized_route_tables
```

The generator validates that:

- the normal table is complete;
- the failed table excludes routes to and from S377;
- no failure state next hop points to S377.

### Verify This Step

Run:

```powershell
python -c "from cases.case3 import main; from cases.case3.experiment.data.centralized_route_tables import load_centralized_route_tables; t=load_centralized_route_tables(); print(t['normal'].shape, t['s377_failed'].shape, (t['s377_failed']==377).sum())"
```

Expected output:

```text
(400, 400) (400, 400) 0
```

For the archive bundled with this release, an additional integrity check is:

```powershell
Get-FileHash cases\case3\experiment\data\centralized_route_tables.npz -Algorithm SHA256
```

Expected SHA-256 for the bundled file:

```text
B983B864F0AC28FC2C7CCF1F3D34D5B92E98AD8775504E43BD958E9764E34F29
```

A newly regenerated `.npz` can have different container metadata and therefore
a different file hash. In that situation, use the matrix shape and
failed-next hop checks above as the functional acceptance criteria.

## 10. Step 8: Add Centralized Routing

### Goal

Register a proactive centralized routing callback that uses the currently
deployed global next hop matrix and preserves stale route caches until the next
deployment.

### Files to Add

Create:

```text
cases/case3/experiment/routing/centralized_control.py
cases/case3/experiment/routing/centralized_routing.py
cases/case3/src/stack/network_layer.py
```

### Ground Network Control Center

`GroundNetworkControlCenter` is an internal routing controller, not an
EasySatSim behavior or entity.

At construction time it loads both matrices into memory. During simulation,
`refresh_if_needed(current_time)` advances the deployment index and selects the
corresponding matrix. It also increases `route_version`.

This is a logical control plane model:

```text
satellite availability state -> predefined route table state
route table version          -> satellite forwarding cache
```

### Centralized Routing Callback

`CentralizedPeriodicRouting.routing_algorithm(...)` obtains a next hop from the
controller:

```python
next_satellite_id = controller.get_next_hop(
    current_time=current_time,
    src_satellite_id=src_satellite_id,
    dst_satellite_id=dst_satellite_id,
)
```

`case_setup.py` registers this callback through:

```python
scene_controller.register_routing_algorithm(
    CentralizedPeriodicRouting.routing_algorithm
)
```

EasySatSim installs the callback as the routing function used by network
protocol `0x0800` when the entity process starts.

### Centralized Network Layer Adapter

Centralized mode replaces the default `0x0800` parse and encapsulation function
with `Case3CentralizedNetworkLayer` while continuing to use the existing
`DataPacket` type.

The adapter adds route version handling:

- a newly cached centralized route receives the current controller version;
- cached routes remain usable while their version is current;
- after a deployment increments the controller version, stale cached routes are
  removed and recalculated from the new matrix.

This is required because replacing only the routing callback would not
invalidate entries already stored in satellite routing tables.

### Verify This Step

Check the deployment sequence without running a simulation:

```powershell
python -c "from cases.case3 import main; from cases.case3.experiment.routing.centralized_control import GroundNetworkControlCenter; c=GroundNetworkControlCenter(50); [(c.refresh_if_needed(t), print(t, c.route_version, c.deployed_table_name)) for t in (0, 50, 100, 105, 150)]"
```

The table names should be:

```text
normal, normal, normal, normal, s377_failed
```

The version remains unchanged between 100 and 105 seconds.

## 11. Step 9: Add Distributed Routing

### Goal

Add a distributed routing callback that preserves EasySatSim's default routing
behavior during normal operation and performs local bypass only when required.

### File to Add

Create:

```text
cases/case3/experiment/routing/distributed_rerouting.py
```

### Reuse Default Minimum Hop Routing

The distributed callback first calls:

```python
default_next_hop_id = MinHopRouting.routing_algorithm(...)
```

The default next hop is returned unchanged if it:

- exists;
- has not already been visited by the packet;
- is currently marked alive.

### Select a Local Bypass

If the default next hop is unavailable, the callback examines the four local
neighbors of the current satellite.

Invalid candidates are removed if they are dead or already visited. Remaining
candidates are ordered by:

```text
1. toroidal distance to the destination
2. neighbor delay
3. satellite id
```

The best candidate becomes the local bypass next hop. If no valid candidate
exists, the callback returns `None` and normal network layer loss handling
applies.

### Register the Callback

Distributed mode uses:

```python
scene_controller.register_routing_algorithm(
    DistributedLocalRerouting.routing_algorithm
)
```

Unlike centralized mode, it does not replace the full `0x0800` network layer
protocol function. It reuses the default EasySatSim network layer logic and
adds only the routing callback.

### Verify This Step

Compile both routing modes:

```powershell
python -m compileall -q cases\case3\experiment\routing cases\case3\src\stack
```

## 12. Step 10: Connect Everything in case_setup.py

### Goal

Connect all Case 3 extensions to a scene that already contains EasySatSim's
default entities, behaviors, and protocol stack.

### Final Configuration Flow

`configure_case3_scene(scene_controller)` performs:

```text
prepare the event log
-> assign the 200 generated user coordinates
-> register and bind permanent failure injection
-> replace default random traffic with controlled pair traffic
-> register application port 18080
-> register centralized or distributed routing
```

### Components Common to Both Modes

Both routing modes use:

- the same constellation;
- the same user grouping and seed model;
- the same controlled pair traffic;
- the same satellite 377 failure behavior;
- the same application port 18080;
- the same event logger and run metadata.

### Centralized Only Components

Centralized mode additionally uses:

- `GroundNetworkControlCenter`;
- the precomputed route table deployment sequence;
- `CentralizedPeriodicRouting`;
- `Case3CentralizedNetworkLayer` for route version handling.

### Distributed Only Component

Distributed mode uses:

- `DistributedLocalRerouting` as the registered routing callback.

This separation ensures that only the routing behavior changes during the comparison while the other settings remain the same.

### Verify This Step

Compile the full case:

```powershell
python -m compileall -q cases\case3
```

## 13. Step 11: Run One Scenario Manually

### Goal

Run one routing mode and one seed for interactive inspection.

### Select Mode and Seed

Edit only these values in:

```text
cases/case3/src/configuration/simulation_config.py
```

```python
CASE3_ROUTING_MODE = "centralized"  # or "distributed"
CASE3_RANDOM_SEED = 20260811
```

### Run

```powershell
python cases\case3\main.py
```

The manual entry enables the EasySatSim visualization. Use the control window
to start the simulation and allow it to reach 200 seconds.

The same entry also accepts process local command line overrides:

```powershell
python cases\case3\main.py --routing mode centralized --seed 20260811
python cases\case3\main.py --routing mode distributed --seed 20260811
```

### Expected Outputs

Each successful run creates three timestamped files under
`cases/case3/experiment/output/`:

```text
easysatsim_result_<mode>_seed_<seed>_<timestamp>.csv
case3_events_<mode>_seed_<seed>_<timestamp>.csv
case3_run_metadata_<mode>_seed_<seed>_<timestamp>.json
```

The network result CSV is the EasySatSim raw network record. The Case 3 event
CSV is used by the two current metrics. The metadata JSON connects both files
to the exact experiment configuration.

New runs record repository relative POSIX paths, for example `cases/case3/experiment/output/<file>`.

## 14. Step 12: Add the Paired Seed Batch Runner

### Goal

Run the same seed once for centralized routing and once for distributed routing,
then repeat this paired design for 1-20 seeds.

### File to Add

Create:

```text
cases/case3/run_experiment.py
```

### Batch Design

The default settings are:

```python
SEED_START = 20260811
SEED_COUNT = 10
```

The default seed range is therefore:

```text
20260811 ... 20260820
```

One seed group always contains both routing modes, so:

```text
N seed groups = 2 * N simulations
```

The batch runner starts one independent headless process at a time. It does not
process metrics or draw figures.

### Output Validation

After every run, the batch script checks that:

- metadata exists;
- the metadata referenced event log exists;
- the metadata referenced network log exists;
- the event log has a valid header;
- both `generate` and `arrival` events exist.

If validation fails, the batch stops.

### Inspect Commands Without Running

```powershell
python cases\case3\run_experiment.py --seed-count 10 --dry-run
```

### Run a Small Experiment

For one paired seed:

```powershell
python cases\case3\run_experiment.py --seed-count 1
```

For three paired seeds:

```powershell
python cases\case3\run_experiment.py --seed-count 3
```

### Run the Paper Experiment

```powershell
python cases\case3\run_experiment.py --seed-count 10
```

The batch creates:

```text
case3_batch_manifest_<timestamp>.json
```

The manifest records planned runs, completed runs, source files, timestamps,
and final status. A complete ten seed experiment should report:

```text
planned_run_count: 20
completed_run_count: 20
status: complete
```

## 15. Step 13: Process the Experiment Metrics

### Goal

Select comparable paired runs, match generated packets to arrivals, and create
the time bin and phase summaries used by plotting and analysis.

### File to Add

Create:

```text
cases/case3/experiment/evaluation/process_results.py
```

### Select Paired Runs

The processor scans all Case 3 metadata files. For each routing mode and seed combination, it selects the newest metadata file. It includes a seed only if both centralized and distributed results exist.

Before processing, it validates comparable settings such as:

- duration;
- failed satellite and failure time;
- centralized deployment interval;
- constellation size;
- user count and pair count;
- coordinate model and subcenters;
- physical layer enable state;
- same coordinate hash for both modes of one seed.

### Use Generation Time Cohorts

The experiment uses five second time bins:

```python
BIN_SECONDS = 5.0
```

For each bin, the cohort contains packets generated during that interval. A
packet is delivered if its `message_id` appears in the arrival log. Only the
first arrival of a duplicated message id is used.

The internal delivery ratio is:

```text
delivery ratio = delivered cohort packets / generated cohort packets
```

The plotted undelivered ratio is:

```text
undelivered ratio = 1 - delivery ratio
```

Average hop count is calculated only for successfully delivered packets from
the same generation time cohort:

```text
average hop count = mean hop count of delivered cohort packets
```

Lost packets have no completed path and therefore do not enter the hop count
mean.

### Phase Definitions

The processor also creates three phase summaries:

```text
normal              0-105 seconds
failure_to_refresh  105-150 seconds
post_refresh        150-200 seconds
```

### Run

```powershell
python -m cases.case3.experiment.evaluation.process_results
```

### Expected Outputs

The command writes:

```text
cases/case3/experiment/output/CASE3_TIME_BIN_METRICS.csv
cases/case3/experiment/output/CASE3_PHASE_SUMMARY.csv
cases/case3/experiment/output/CASE3_RUN_MANIFEST.csv
cases/case3/experiment/output/CASE3_FINAL_RESULTS_REPORT.md
```

Its console output lists every selected metadata and event file, the paired
seeds, and the number of processed runs.

## 16. Step 14: Generate the Paper Figures

### Goal

Aggregate the paired seed time series and generate one undelivered ratio figure
and one average hop count figure with a shared style.

### Files to Add

Create:

```text
cases/case3/plotting/
  _common.py
  plot_undelivered_ratio.py
  plot_average_hop_count.py
  plot_all_figures.py
```

### Shared Figure Logic

`_common.py` loads:

```text
CASE3_TIME_BIN_METRICS.csv
CASE3_RUN_MANIFEST.csv
```

For each mode and time bin center, it calculates:

```text
line        mean across paired seeds
color band  plus or minus one standard deviation across paired seeds
```

The figure style uses:

```text
red circles       Centralized Routing
blue triangles    Distributed Routing
gray dashed line  failure boundary at 105 seconds
gray dashed line  centralized deployment boundary at 150 seconds
light gray area   post failure interval beginning at 105 seconds
```

### Undelivered-Ratio Figure

`plot_undelivered_ratio.py` calculates:

```python
undelivered_ratio = 1.0 - delivery_ratio
```

Output:

```text
cases/case3/plotting/figures/CASE3_UNDELIVERED_RATIO.png
```

### Average-Hop-Count Figure

`plot_average_hop_count.py` displays the hop count of successfully delivered packets.

Output:

```text
cases/case3/plotting/figures/CASE3_AVERAGE_HOP_COUNT.png
```

### Run

Generate both figures:

```powershell
python -m cases.case3.plotting.plot_all_figures
```

Redraw an individual figure:

```powershell
python -m cases.case3.plotting.plot_undelivered_ratio
python -m cases.case3.plotting.plot_average_hop_count
```

The plotting command prints all source event files and reports the number of
runs and seeds included in the curves.

## 17. Full Reproduction Workflow

Run from the EasySatSim repository root. The repository may be placed in any
user directory or drive; no author specific path is required.

### 1. Prepare a Clean Reproduction

Install the complete Case 3 environment:

```powershell
python -m pip install -r cases/case3/requirements.txt
```

Move old files under `cases/case3/experiment/output/` and old Case 3 figures
to a separate backup directory, or use a fresh checkout. Keep
`centralized_route_tables.npz`: it is a validated experiment input, not a
generated run result. Starting from an empty output directory prevents the
processor from selecting metadata left by an earlier batch.

Clear Case 3 overrides left by an earlier PowerShell session:

```powershell
Remove-Item Env:EASYSATSIM_CASE3_ROUTING_MODE -ErrorAction SilentlyContinue
Remove-Item Env:EASYSATSIM_CASE3_RANDOM_SEED -ErrorAction SilentlyContinue
Remove-Item Env:EASYSATSIM_CASE3_OUTPUT_TIMESTAMP -ErrorAction SilentlyContinue
```

Confirm the default mode, seed, and output prefix:

```powershell
python -c "from cases.case3 import main; print(main.cg.CASE3_ROUTING_MODE); print(main.cg.CASE3_RANDOM_SEED); print(main.cg.OUTPUT_PREFIX)"
```

Expected output:

```text
centralized
20260811
centralized_seed_20260811
```

### 2. Check the Sources and Route Tables

```powershell
python -m compileall -q cases\case3
```

A successful command exits without a traceback. Then load and validate the
precomputed centralized tables:

```powershell
python -c "from cases.case3 import main; from cases.case3.experiment.data.centralized_route_tables import load_centralized_route_tables; t=load_centralized_route_tables(); print(t['normal'].shape, t['s377_failed'].shape, (t['s377_failed']==377).sum())"
```

Expected output is `(400, 400) (400, 400) 0`.

### 3. Inspect the Batch Without Running It

```powershell
python cases\case3\run_experiment.py --seed-count 10 --dry-run
```

Confirm that the command prints 20 planned simulations covering seeds
20260811-20260820 and both `centralized` and `distributed` modes.

### 4. Run the Ten Paired Seeds

```powershell
python cases\case3\run_experiment.py --seed-count 10
```

This command performs 20 sequential headless simulations. Every run represents 200 seconds, so the configured simulation time alone is 66 minutes 40 seconds.

The batch only runs the simulations and checks their outputs. It does not process metrics or draw figures.

Do not start a second Case 3 batch in the same output directory while the first
one is active. On success, the final message should report 20 completed
simulations and a batch manifest with `status: complete`.

### 5. Process Metrics

```powershell
python -m cases.case3.experiment.evaluation.process_results
```

Confirm that the console reports:

```text
20 runs
10 paired seeds
2 routing modes
```

The processor should create 800 time bin rows, six phase summary rows, and 20
run manifest rows before writing its Markdown report.

### 6. Generate Both Figures

```powershell
python -m cases.case3.plotting.plot_all_figures
```

Final figure files:

```text
cases/case3/plotting/figures/CASE3_UNDELIVERED_RATIO.png
cases/case3/plotting/figures/CASE3_AVERAGE_HOP_COUNT.png
```

Confirm that the plotting console reports 20 runs, 10 seeds, two routing modes,
and two created figures.

## 18. Expected Outputs and Acceptance Criteria

### Output Checklist

Starting from an empty output directory, a complete ten seed reproduction
should produce:

| Output | Expected count or content |
| --- | --- |
| Network result CSVs | 20: one per mode and seed |
| Case 3 event CSVs | 20: one per mode and seed |
| Run metadata JSON files | 20: one per mode and seed |
| Batch manifest JSON | One complete manifest for the batch |
| `CASE3_TIME_BIN_METRICS.csv` | 800 rows: 20 runs x 40 five second bins |
| `CASE3_PHASE_SUMMARY.csv` | Six rows: two modes x three phases |
| `CASE3_RUN_MANIFEST.csv` | 20 selected paired run rows |
| `CASE3_FINAL_RESULTS_REPORT.md` | One human readable phase report |
| Paper figures | Two nonempty PNG files |

Repeated or interrupted batches can leave additional timestamped raw files and
partial manifests. In that situation, rely on the processor's selected run
manifest rather than the total directory file count.

### Structural Checks

- The complete batch manifest must report `planned_run_count = 20`,
  `completed_run_count = 20`, and `status = complete`.
- Every seed from 20260811 through 20260820 must have one centralized and one
  distributed metadata row.
- Every event file must contain usable `generate` and `arrival` events and one
  `satellite_failure` event near 105 seconds.
- Every network CSV should span approximately 0-199 seconds and contain the
  standard EasySatSim generated, arrived, lost, latency, and hop fields.
- The plotting console must identify 10 paired seeds. A single mode or incomplete
  seed set is not a valid paper comparison.

### Reference Results

With the current ten paired seeds, the expected qualitative behavior and
practical consistency ranges are:

| Phase and metric | Centralized reference | Distributed reference |
| --- | --- | --- |
| Normal undelivered ratio | below 1% | below 1% |
| 105-150 s undelivered ratio | 50%-65% | 1%-3% |
| Post Refresh undelivered ratio | below 1% | below 1% |
| 105-150 s average hop count | 7.8-8.3 | 8.4-8.9 |

During 105-150 seconds, the centralized undelivered ratio should rise sharply because the routing table deployed at 100 seconds may still point to failed satellite 377. These values are only validation reference ranges. Missing timeline
boundaries, no centralized degradation, no distributed hop increase, a single
routing curve, or values far outside these ranges should be investigated before
the figures are used in the paper.

## 19. Troubleshooting

### `ModuleNotFoundError: No module named 'src.tools'`

Run commands from the EasySatSim project root:

```powershell
python cases\case3\main.py
```

Do not run `main.py` with `cases/case3` as the working directory. The entry point
must be able to place the project root before the case local `src/` directory in
`sys.path`.

### Precomputed Route Tables Were Not Found

If the error mentions `centralized_route_tables.npz`, regenerate it:

```powershell
python -m cases.case3.experiment.data.generate_centralized_route_tables
```

Do not regenerate the table after changing only the random seed. User
coordinates do not affect these topology only satellite route matrices.

### Route Table Archive Does Not Match the Configuration

The loader validates:

```text
orbit number
satellites per orbit
failed satellite id
matrix shape
```

If one of these values was intentionally changed, regenerate the archive. If it
was not intentionally changed, restore the fixed Case 3 configuration.

### The Batch Stops After One Run

Read the final batch message and partial manifest. The runner stops if an event
or network file is missing, the event header is invalid, or no usable generate
and arrival events exist.

Fix the reported run before restarting. Do not process a partial seed as if it
were a complete paired comparison.

The batch runner does not resume inside an existing manifest. Starting it again
creates a new manifest and reruns the requested seed sequence. For the cleanest
paper reproduction, move the partial batch's raw files and manifest to a backup
directory before restarting all ten seeds. If raw files from several attempts
are retained, the processor selects the newest metadata for each mode and seed
and still applies its comparability checks, but the total number of files in
the directory will be greater than the clean run checklist.

### Metric Processing Selects an Older Attempt

If timestamps or copied file modification times make that choice unclear, inspect the printed source file list and `CASE3_RUN_MANIFEST.csv`. Move superseded attempts out of the output directory,
rerun metric processing, and confirm that all 20 selected rows belong to the
intended experiment definition.

### Only One Routing Curve Appears

First rerun metric processing:

```powershell
python -m cases.case3.experiment.evaluation.process_results
```

Check that it reports both modes for every paired seed. The processor rejects
event logs that contain no generation or arrival events, preventing a silent
single curve result.

Then redraw:

```powershell
python -m cases.case3.plotting.plot_all_figures
```

### The Failure Does Not Occur Near 105 Seconds

Check the event log for `satellite_failure`. The precomputed route table design
removes online 400-by-400 route calculation from the simulation loop, so the
failure should occur close to 105 seconds.

If a large delay reappears, verify that centralized routing loads
`centralized_route_tables.npz` rather than calculating full route tables during
`refresh_if_needed()`.

### Centralized Routing Does Not Recover at 150 Seconds

Verify the deployment sequence:

```text
normal, normal, normal, s377_failed
```

and the deployment times:

```text
0, 50, 100, 150 seconds
```

Also verify that the failure state matrix contains no next hop equal to 377.

### Results from the Two Modes Are Not Comparable

The processor compares metadata before generating metrics. If it reports a
mismatch, check:

```text
failure satellite and time
centralized deployment interval
constellation dimensions
user and pair counts
coordinate model and seed
coordinate hash
physical layer enable state
```

Do not bypass this check. Rerun the mismatched routing mode with the correct
configuration and same seed.

### Figure Generation Fails

Process the metrics first:

```powershell
python -m cases.case3.experiment.evaluation.process_results
```

The plotting scripts require:

```text
CASE3_TIME_BIN_METRICS.csv
CASE3_RUN_MANIFEST.csv
```

### The Figure Values Do Not Match the Paper Text

Confirm that the figure was generated from the intended ten paired seeds. The
plotting command prints every included event file and seed.

Also remember:

- the first figure displays undelivered ratio, not delivery ratio;
- the line is the mean across seeds;
- the translucent band is plus or minus one standard deviation;
- hop count includes only successfully delivered packets;
- the two dashed boundaries are 105 and 150 seconds.

If the configuration or seed set changes, regenerate the metrics, figures, and
paper values together.