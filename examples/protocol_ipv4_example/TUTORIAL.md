# Tutorial: Integrating Scapy IPv4/UDP with EasySatSim

## 1. Goal and Scope

This example shows how to integrate Scapy based IPv4/UDP protocol processing into EasySatSim. The application layer first generates a `DataMessage`, which is then encapsulated into standard format UDP bytes and further encapsulated into standard format IPv4 bytes. The resulting IPv4 packet continues through the existing EasySatSim link and physical layer processing mechanisms and is forwarded across the satellite network over multiple hops. When the packet reaches the destination, IPv4 and UDP data are parsed in reverse order to recover the original application layer `DataMessage`.

During this process, the transport and network layers use `bytes` as the actual data representation passed across layers and processes. Scapy is mainly used to construct and parse UDP/IPv4 packets. Its packet objects exist only temporarily inside specific protocol processing functions and are not passed as persistent data objects between EasySatSim layers or processes.

## 2. How to Use This Tutorial

Complete the following workflow from the EasySatSim project root:

1. Install the EasySatSim core dependencies.
2. Install the Scapy and plotting dependencies required by this example.
3. Run `main.py` to execute and validate the deterministic scenario.
4. Confirm that all 24 required assertions pass.
5. Run `show_result.py` to inspect the stored validation evidence and generate the figure.
6. If needed, open the two PCAP files with Wireshark.

This is a protocol integration example rather than a case study. It uses only one deterministic packet so that protocol registration, serialized bytes, routing, TTL changes, and checksums can be checked exactly.

## 3. Implementation Map

The entire example is located under `examples/protocol_ipv4_example`. The main files and their roles are:

| File | Responsibility |
| --- | --- |
| `main.py` | Runs the scenario, prepares clean output files, and invokes end to end validation. |
| `example_setup.py` | Builds the example specific protocol stack and registers the application, UDP, and IPv4 handlers. |
| `src/configuration/simulation_config.py` | Defines the constellation, users, packet, physical layer, and output paths. |
| `src/behaviors/ipv4_demo_traffic.py` | Generates the single deterministic application message. |
| `src/stack/application_layer.py` | Connects application port 18080 to the example traffic behavior. |
| `src/stack/scapy_udp_data.py` | Stores and validates serialized UDP bytes. |
| `src/stack/scapy_udp_protocol.py` | Encapsulates and parses UDP datagrams. |
| `src/stack/scapy_ipv4_data.py` | Stores and validates serialized IPv4 bytes. |
| `src/stack/scapy_ipv4_protocol.py` | Encapsulates, parses, and forwards IPv4 packets, including TTL and checksum updates. |
| `experiment/integration/ipv4_trace_logger.py` | Records actual hop by hop forwarding and delivery events. |
| `experiment/integration/pcap_writer.py` | Exports source and destination packets as standard PCAP files. |
| `experiment/evaluation/validate_ipv4_example.py` | Performs the 24 end to end assertions. |
| `experiment/evaluation/validate_stack_registration.py` | Verifies the example specific protocol registration and confirms that the default stack remains unchanged. |
| `show_result.py` | Reads the stored validation evidence, prints a human readable summary, and generates the result figure. |

## 4. Default Network Layer and Example Specific Network Layer

The default EasySatSim protocol stack maps `network/0x0800` to its internal `Type0x0800` handler and simplified `DataPacket`. `DataPacket` is not defined as a serialized standard IPv4 packet.

This example first loads the default protocol stack and then modifies only its own `StackManager`:

```text
application / port 18080 -> IPv4DemoApplicationPort -> DataMessage
transport   / protocol 17 -> ScapyUDPProtocol       -> ScapyUDPData
network     / EtherType 0x0800 -> ScapyIPv4Protocol -> ScapyIPv4Data
link        / Ethernet -> existing EasySatSim handler
physical    / Ethernet -> existing EasySatSim handler
```

The application and UDP entries are added to the stack, while the existing `network/0x0800` entry is replaced through the following public manager APIs:

```python
replace_protocol_func(
    layer_name,
    protocol_name,
    parse_func,
    encapsulate_func,
)

replace_relationship(
    layer_name,
    protocol_name,
    data_name,
)
```

Both APIs raise `KeyError` if the target entry does not exist. A newly created default stack manager remains unchanged.

## 5. Install the Dependencies

First install the EasySatSim core dependencies according to the project `README.md` or `docs/getting_started.md`:

```powershell
python -m pip install -r requirements.txt
```

The tested Scapy and Matplotlib versions for this example are fixed in its own `requirements.txt`:

```powershell
python -m pip install -r examples/protocol_ipv4_example/requirements.txt
```

Scapy is used for protocol implementation, PCAP export, and validation. Matplotlib is used only when `show_result.py` generates the presentation figure. Wireshark is optional and is not required to run or validate the simulation.

## 6. UDP Implementation

`src/stack/scapy_udp_data.py` uses `ScapyUDPData` to store serialized UDP bytes and checks the minimum UDP header length and the UDP length field.

`src/stack/scapy_udp_protocol.py` implements the following functions:

- encapsulating application bytes into a standard UDP datagram;
- parsing standard UDP bytes back into application bytes;
- propagating source and destination ports;
- dispatching through standard IP protocol number 17.

This example uses port `18080` at both endpoints.

## 7. IPv4 Implementation

`src/stack/scapy_ipv4_data.py` uses `ScapyIPv4Data` to store serialized IPv4 bytes and validates:

- IPv4 version 4;
- IHL 5;
- total length consistency;
- absence of fragmentation;
- a valid IPv4 header checksum.

`src/stack/scapy_ipv4_protocol.py` constructs an IPv4 packet at the source with TTL 64, protocol 17, and Identification 8001.

At each satellite that is not the destination, the following processing is performed:

1. Parse the standard IPv4 bytes.
2. Check for forwarding loops and TTL exhaustion.
3. Decrease the TTL by one.
4. Remove the old header checksum.
5. Serialize again with Scapy and calculate the new checksum.
6. Validate the regenerated IPv4 bytes.
7. Obtain the next hop through the EasySatSim route cache and routing callback.
8. Pass the packet to the existing link and physical layer processing.

When the packet reaches the destination user, the TTL is not decreased again. Protocol number 17 is passed upward to the UDP parser, and port 18080 is then passed to the application layer.

## 8. Deterministic Multi Hop Scenario

This example uses an 8×12 Walker style constellation:

```text
satellites: 96
users:       2
User 0:      (0.0, 0.0), access satellite 0
User 1:      (36.901843657, -79.459413647), access satellite 40
payload:     EASYSATSIM_STANDARD_IPV4_UDP_TEST
```

The scenario contains only one packet. The actual route is generated by the EasySatSim routing callback, and the example does not hard code the complete hop list.

The validated route is:

```text
User 0
  -> Satellite 0 -> 1 -> 13 -> 14 -> 26 -> 27 -> 39 -> 40
  -> User 1
```

Eight satellites perform IPv4 forwarding. Final delivery to the destination user is not counted as a forwarding event.

## 9. Trace and PCAP Evidence

`experiment/integration/ipv4_trace_logger.py` records every actual forwarding and delivery event in `experiment/output/ipv4_hop_trace.csv`, including:

- simulation time and entity identity;
- source and destination IP addresses and protocol number;
- TTL before and after processing;
- checksum before and after processing;
- next hop IP/entity and action.

`experiment/integration/pcap_writer.py` exports:

```text
source_ipv4_udp.pcap
destination_ipv4_udp.pcap
```

Both files are standard libpcap files with link type `DLT_RAW` 12, so each record begins directly with an IPv4 header.

The timestamp mapping is:

```text
pcap timestamp = 1700000000 + simulation time
```

The warning `No libpcap provider available` affects only live capture support.

## 10. Run and Validate

Run from the project root:

```powershell
python examples/protocol_ipv4_example/main.py
```

The entry program first clears old output files, runs the short deterministic scenario, and then invokes the consolidated end to end validator.

A successful run should end with:

```text
[IPv4 Example] PASS: 24/24 required assertions passed; initial TTL 64, final TTL 56, forwarding events 8.
```

`main.py` generates the following six files:

```text
examples/protocol_ipv4_example/experiment/output/step8_delivery.json
examples/protocol_ipv4_example/experiment/output/step8_network_metrics.csv
examples/protocol_ipv4_example/experiment/output/ipv4_hop_trace.csv
examples/protocol_ipv4_example/experiment/output/source_ipv4_udp.pcap
examples/protocol_ipv4_example/experiment/output/destination_ipv4_udp.pcap
examples/protocol_ipv4_example/experiment/output/ipv4_validation_summary.json
```

The output directory can be cleared before a run. These files will be generated again.

To revalidate existing outputs without rerunning the simulation, run:

```powershell
python -m examples.protocol_ipv4_example.experiment.evaluation.validate_ipv4_example
```

To verify the example specific protocol registration and isolation from the default protocol stack, run:

```powershell
python -m examples.protocol_ipv4_example.experiment.evaluation.validate_stack_registration
```

The comprehensive validator independently checks the PCAP file structure and raw bytes, delivery identity, IPv4/UDP fields, route continuity, event ordering, per hop TTL transitions, per hop checksum recalculation, final packet consistency, and timestamp mapping.

### 10.1 Acceptance Criteria

The example is considered successful when all of the following conditions are satisfied:

- `main.py` exits normally and prints `PASS: 24/24 required assertions passed`;
- the reported initial TTL is 64, final TTL is 56, and the forwarding event count is 8;
- all six files listed above exist and are nonempty;
- `ipv4_validation_summary.json` reports an overall `PASS` status with no failed assertions;
- the standalone validation command also exits successfully;
- the stack registration validator confirms that the example registration did not modify a fresh default protocol stack.

## 11. Present the Result

After `main.py` succeeds, run:

```powershell
python examples/protocol_ipv4_example/show_result.py
```

The script reads the generated JSON, CSV, and PCAP evidence and prints:

- the actual registration differences between the default and example protocol stacks;
- source and destination IPv4/UDP fields;
- TTL and checksum transitions at each satellite;
- the actual route and end to end summary;
- absolute source and destination PCAP paths for Wireshark.

The script also generates:

```text
examples/protocol_ipv4_example/experiment/output/PROTOCOL_IPV4_RESULT.png
```

## 12. Inspect the PCAP Files with Wireshark

After `main.py` succeeds, open the following files with Wireshark:

```text
examples/protocol_ipv4_example/experiment/output/source_ipv4_udp.pcap
examples/protocol_ipv4_example/experiment/output/destination_ipv4_udp.pcap
```

Use the display filter:

```text
ip && udp
```

Each PCAP contains only one serialized packet.

Expand `Internet Protocol Version 4` and `User Datagram Protocol`, then compare the following fields:

| Field | Source capture | Destination capture |
| --- | --- | --- |
| IP version | 4   | 4   |
| IP protocol | 17 (UDP) | 17 (UDP) |
| UDP port | 18080 | 18080 |
| TTL | 64  | 56  |
| Payload | `EASYSATSIM_STANDARD_IPV4_UDP_TEST` | unchanged |

The source and destination IP addresses remain unchanged, while the IPv4 header checksum changes as the TTL is updated during forwarding.

If you want Wireshark to explicitly label checksum validity, you may need to enable IPv4 checksum validation in its protocol preferences.

Both PCAP files use `DLT_RAW`, so Wireshark can directly parse IPv4, UDP, and Data without displaying an Ethernet header.

The absence of an Ethernet layer does not mean that the packet is missing a component. This example intentionally exports the authoritative network layer byte representation.

## 13. Troubleshooting

### `ModuleNotFoundError` When Starting the Example

Run commands from the project root and install both the project level and example specific requirements:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r examples/protocol_ipv4_example/requirements.txt
```

### `No libpcap provider available` Warning

This warning is related to Scapy live network interface capture support.

This example writes offline PCAP files directly and does not require a libpcap provider. Continue the run and use the final validation result to determine success.

### Output Is Missing, Incomplete, or from an Older Run

Run `main.py` again.

The program clears known old output files before starting and regenerates the complete result set.

Do not run `show_result.py` first because it only reads existing evidence and does not rerun the simulation.

### The Validator Reports `FAIL`

Inspect:

```text
examples/protocol_ipv4_example/experiment/output/ipv4_validation_summary.json
```

The `failed_assertions` and `assertions` fields provide the expected and observed values.

Before investigating the failure further, rerun `main.py` to exclude stale files or incomplete outputs.

### Wireshark Does Not Show an Ethernet Header

This is expected for a `DLT_RAW` capture.

Inspect the IPv4 and UDP sections directly. This example exports the network layer packet rather than an Ethernet frame captured from a real physical network interface.

### The Presentation Figure Is Not Generated

First confirm that `main.py` has passed validation. Then install the example specific dependencies and run `show_result.py`.

The plotting command reads the six stored output files and generates `PROTOCOL_IPV4_RESULT.png` without rerunning the scenario.

## 14. What the Result Demonstrates

Supported conclusion:

> EasySatSim can integrate standard format IPv4/UDP packet bytes and execute selected IPv4 protocol processing logic inside the simulator while reusing its existing satellite network functions.