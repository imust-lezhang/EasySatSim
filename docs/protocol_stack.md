# Protocol Stack Extension

This guide explains how to register protocol data, protocol processing functions, mappings, and routing logic without replacing the entire EasySatSim protocol stack.

## Protocol Stack Model

Each layer in EasySatSim uses a protocol identifier to select the corresponding processing function and data type. The default protocol stack contains the application, transport, network, data link, and physical layers.

During data transmission, processing proceeds downward in the following order:

```text
application -> transport -> network -> data link -> physical
```

During data reception, processing proceeds upward in the reverse order:

```text
physical -> data link -> network -> transport -> application
```

In general, adding a complete new protocol entry requires three types of registration:

```python
stack_manager.add_protocol_data(
    layer_name="application",
    data_name="my_message",
    data_type=MyMessage,
    to_data_func=MyMessage.to_data,
    data_to_func=MyMessage.data_to,
)

stack_manager.add_protocol_func(
    layer_name="application",
    protocol_name=18080,
    parse_func=MyPort.parse_and_process_func,
    encapsulate_func=MyPort.encapsulate_func,
)

stack_manager.add_relationship(
    layer_name="application",
    protocol_name=18080,
    data_name="my_message",
)
```

If an existing data type already meets the requirements, only the protocol processing function and mapping need to be added. For example, Case 3 registers application port `18080` and associates it with the existing `data_message` data type.

## Protocol Data

A protocol data class represents the object or byte data processed by a protocol layer and provides the data conversion functions required by the manager mappings.

When designing protocol data, the primary representation of the data inside EasySatSim should be clearly defined:

- EasySatSim default protocols use internal data classes;
- for standard format protocols, serialized `bytes` should be used as the primary form for transfer across protocol layers and processes;
- objects produced by third party parsers should be treated as temporary objects and should not be shared directly between worker processes.

The Scapy example replaces the mapping for network protocol `0x0800` and associates it with a byte based IPv4 data type, enabling the processing of standard IPv4/UDP packets.

## Protocol Processing Functions

A protocol usually provides two types of processing functions:

- `encapsulate_func`: receives data from the upper layer, fills in the fields required by the current protocol layer, and passes the processed data downward;
- `parse_and_process_func`: validates and processes incoming data, then decides whether to continue forwarding, deliver the data upward, or discard it.

Data field checks should be performed as much as possible at the protocol layer responsible for those fields.

For example, the IPv4 example checks fields such as the IPv4 version, IHL, total length, header checksum, fragmentation state, TTL, source address, destination address, and protocol number at the network layer.

## Adding and Replacing Protocols

When the target protocol identifier does not yet exist, use:

```python
add_protocol_func()
add_relationship()
```

Registering an existing protocol identifier again raises a `KeyError`.

When an existing protocol identifier needs to be modified, use the public replacement interfaces:

```python
stack_manager.replace_protocol_func(
    layer_name="network",
    protocol_name=0x0800,
    parse_func=MyIPv4.parse_and_process_func,
    encapsulate_func=MyIPv4.encapsulate_func,
)

stack_manager.replace_relationship(
    layer_name="network",
    protocol_name=0x0800,
    data_name="my_ipv4_data",
)
```

The replacement interfaces do not accept a protocol layer or target protocol that does not exist. This prevents extension code from silently creating an incompletely registered protocol stack entry when the intended target is absent.

## Application Layer Extension

Application services are usually distinguished by port numbers. Their processing functions generally need to define:

- which message type is accepted;
- how the destination entity processes the message;
- which lower layer protocol identifier receives the encapsulated data;
- whether logs or case specific events need to be recorded.

All three cases use application layer extensions:

- Case 1 uses satellite application port `22` for IDS detection;
- Case 3 uses port `18080` to generate controlled paired communication traffic;
- Case 2 defines custom application layer data for learning samples and model updates.

## Transport Layer and Network Layer Extension

Transport layer logic mainly handles transport fields such as ports and related checks.

Network layer logic is mainly responsible for addressing, packet forwarding, route lookup, and network header state.

Replacing only the routing callback is sufficient only when the existing network layer data format and route cache mechanism remain applicable.

A routing callback can be registered through the scene controller:

```python
scene_controller.register_routing_algorithm(
    MyRouting.routing_algorithm
)
```

The callback should return a valid next hop entity or identifier in the format required by the default network layer. If no route is available, it should return `None`.

## Data Link Layer and Physical Layer

The default protocol stack uses `"Ethernet"` as the protocol name for the processing functions associated with the data link and physical layers.

General protocol extension examples can usually continue to reuse the default data link and physical layer processing flow.

Replacing these layers changes frame processing, link validity checks, or link state processing, so it requires more extensive testing than simply adding an application port.

## Registration Order

We recommend completing scene and protocol extensions in the following order:

1. create the scene;
2. load the default behaviors;
3. load the default protocol stack;
4. add or replace protocol data;
5. add or replace protocol processing functions;
6. add or replace mappings;
7. register a routing callback if needed;
8. complete the scene configuration;
9. run the simulation.

Registering extensions before `default_stack()` may cause conflicts with the default protocol stack loading process.

Registering extensions after `configuration_complete()` is beyond the normal extension registration stage.

## Verification

Protocol integration should be verified at three levels:

1. **Registration verification**  
  Check whether the target protocol layer and protocol identifier resolve to the intended processing function and data type, while confirming that the unchanged default manager remains in its original state.
  
2. **Protocol layer behavior verification**  
  Check whether encapsulation and parsing preserve fields correctly, reject invalid data, and pass data to the correct adjacent protocol layer.
  
3. **End to end forwarding verification**  
  Check whether packets can be forwarded through multiple satellites, whether the destination receives the original application data, and whether the expected processing at each hop can be examined through the generated evidence.
  

The IPv4/UDP example provided in the repository performs these checks:

```powershell
python examples/protocol_ipv4_example/main.py
python -m examples.protocol_ipv4_example.experiment.evaluation.validate_stack_registration
python -m examples.protocol_ipv4_example.experiment.evaluation.validate_ipv4_example
python examples/protocol_ipv4_example/show_result.py
```

The example generates raw IP PCAP files that Wireshark can parse as IPv4/UDP.

These PCAP files are offline results exported after the simulation, not packets captured in real time from a physical network interface.

This example verifies that **standard format IPv4/UDP packet bytes and selected protocol processing logic can run inside EasySatSim**.