# Configuration Reference

EasySatSim configuration files are executable Python modules. Configuration values may use Python expressions, but the files should remain primarily declarative and should not execute simulation tasks or produce external side effects.

## Configuration File Locations

The default simulator uses:

```text
configuration/simulation_config.py          active configuration
configuration/simulation_config.default.py  reference/default configuration
configuration/simulation_config.*.py        named preset configurations
```

Complete cases use independent configuration files located at:

```text
cases/<case>/src/configuration/simulation_config.py
```

Case specific fields are documented in the corresponding `TUTORIAL.md`. Unless the main simulator also defines and uses these fields, case specific fields should not be copied directly into presets in the main directory.

## Constellation Parameters

| Field | Meaning |
| --- | --- |
| `ORBIT_NUMBER` | Number of orbital planes. |
| `SATELLITE_NUMBER_PRE_ORBIT` | Number of satellites in each orbital plane. |
| `ORBIT_INCLINATION` | Orbital inclination in degrees. |
| `ORBIT_HEIGHT` | Orbital altitude in kilometers. |
| `ORBIT_OMEGA` | Relative phase offset between adjacent orbital planes. |
| `TOTAL_SATELLITE_NUMBER` | Total number of satellites, equal to the number of orbital planes multiplied by the number of satellites per plane. |

## Satellite Parameters

| Field | Meaning |
| --- | --- |
| `SATELLITE_CONE_ANGLE` | Full satellite coverage cone angle in degrees; the valid range is greater than 0 and less than 180. |
| `COVER_RADIUS` | Ground coverage radius used for user access calculations. |
| `BUFFER_MAX_BYTE` | Maximum satellite buffer capacity in bytes. |
| `SATELLITE_ROUTING_UPDATE_TIME` | Refresh interval associated with satellite routing cache entries. |
| `SATELLITE_NEIGHBOR_UPDATE_TIME` | Interval between satellite neighbor information announcements. |
| `MAX_NEIGHBOR_UPDATE_TIME` | Maximum time neighbor information is retained before removal. |

The main configuration calculates the coverage radius as:

```python
COVER_RADIUS = np.tan(np.radians(SATELLITE_CONE_ANGLE / 2)) * ORBIT_HEIGHT
```

Some research cases use a more detailed elevation angle geometry model. These calculations remain within the configuration and implementation of the corresponding case.

## User Parameters

| Field | Meaning |
| --- | --- |
| `USER_NUMBER` | Number of ground users. |
| `USER_LATITUDE_MIN`, `USER_LATITUDE_MAX` | Latitude range used when randomly generating user locations. |
| `USER_DATA_RATE_MIN`, `USER_DATA_RATE_MAX` | Lower and upper bounds of the random payload size used for user traffic generation. |
| `DATA_SCALING` | Scaling factor applied to the generated payload size input. |
| `USER_ROUTING_UPDATE_TIME` | User routing table refresh interval. |
| `POPULATION_PATH` | Path to the population matrix used for user location generation. Relative paths are resolved from `src/`. |

For experiments that require reproducibility, we recommend storing the random seed in the case configuration.

## Link Parameters

| Field | Meaning |
| --- | --- |
| `LINK_TRANSMIT_RATE` | Compatible static transmission rate used when dynamic physical layer rate calculation is disabled. |
| `SERVICE_RATE` | Buffer service rate used to estimate queueing delay. |
| `PROCESSING_TIME` | Default entity processing delay in milliseconds. |

## Physical Layer Switches

| Field | Meaning |
| --- | --- |
| `PHYSICAL_LAYER_ENABLE` | Enables the link level physical layer approximation model. |
| `PHYSICAL_LAYER_ENABLE_DOPPLER` | Enables Doppler related calculations and losses. |
| `PHYSICAL_LAYER_ENABLE_DYNAMIC_RATE` | Maps link state to a dynamic transmission rate. |
| `PHYSICAL_LAYER_UPDATE_INTERVAL` | Cache and update interval for link state calculations. |
| `PHYSICAL_LAYER_USE_CACHE` | Reuses the most recent link state calculation result. |
| `PHYSICAL_LAYER_DEFAULT_PROCESSING_TIME` | Processing delay used by the physical layer model. |

When `PHYSICAL_LAYER_ENABLE` is false, the simulator continues to use the compatible static processing mode. When enabled, ISL and SGL parameters jointly determine link state, transmission rate, delay, and may further affect link availability.

## ISL and SGL Link Budget Parameters

The prefixes `ISL_` and `SGL_` refer to inter satellite links and satellite ground links, respectively. Both groups use the same field structure:

| Suffix | Meaning |
| --- | --- |
| `CARRIER_FREQUENCY_HZ` | Carrier frequency in Hz. |
| `BANDWIDTH_HZ` | Channel bandwidth in Hz. |
| `TX_POWER_DBM` | Transmit power in dBm. |
| `TX_ANTENNA_GAIN_DBI`, `RX_ANTENNA_GAIN_DBI` | Transmit and receive antenna gains in dBi. |
| `SYSTEM_LOSS_DB` | Aggregate system loss in dB. |
| `ATMOSPHERIC_LOSS_DB` | Approximate atmospheric loss in dB. |
| `NOISE_FIGURE_DB` | Receiver noise figure in dB. |
| `MIN_SNR_DB` | Minimum acceptable signal to noise ratio. |
| `MAX_DISTANCE_M` | Maximum link distance allowed by the model, in meters. |
| `DOPPLER_COMPENSATION_HZ` | Frequency offset that the receiver can compensate. |
| `RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB` | Additional loss per kHz beyond the compensation range. |
| `STATIC_RATE_BPS` | Static fallback rate. |
| `MIN_EFFECTIVE_RATE_BPS` | Lower bound of the acceptable effective rate. |
| `SPECTRAL_EFFICIENCY` | Spectral efficiency factor used in rate calculation. |
| `RATE_MAPPING_MODE` | Rate mapping mode; the current supplied configuration uses `"discrete"`. |
| `DROP_LINK_IF_DOPPLER_EXCEEDED` | If true, the link may be marked unavailable when Doppler exceeds the allowed range. |
| `DISCRETE_RATE_TABLE` | Ordered table of `(minimum SNR in dB, rate in bit/s)`. |

Physical layer parameters should be adjusted as a coherent set of link budget parameters.

## Time and Result Output

| Field | Meaning |
| --- | --- |
| `NETWORK_RUNNING_STEP_SECOND` | Simulation time advanced at each global timer update. The default value is 0.05 seconds. |
| `SAVE_FILE_PATH` | Path of the network result CSV file. The interface automatically assigns a timestamped path at the start of each simulation. |

## Editing Configuration and Using Presets in the Interface

`Configuration > Edit Configuration` is used to edit the active configuration file before the simulation starts.

`Configuration > Configuration Presets` is used to apply supplied presets or user saved presets. When applying a configuration file, the program checks:

- whether the filename matches `simulation_config*.py`;
- whether Python syntax and evaluation succeed;
- whether all expected uppercase configuration fields are present;
- whether unexpected uppercase configuration fields are present;
- whether the field order matches `simulation_config.default.py`.

A custom preset is saved as:

`simulation_config.<name>.py`

Only `<name>` needs to be entered in the dialog.

## Configuration Rules for Comparative Experiments

When comparing two methods, all settings unrelated to the methods being compared should remain identical, including:

- constellation and user locations;
- traffic and packet sizes;
- random seed;
- physical layer settings;
- simulation duration and time step;
- failure or event schedule;
- metric definitions and grouping methods.

Each result reported in the paper should retain the corresponding configuration snapshot or metadata. See the [Experiment Guide](experiment_guide.md) for more details.