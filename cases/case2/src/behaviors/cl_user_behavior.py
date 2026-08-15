from collections import deque

from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore

from cases.case2.experiment.integration.case2_event_logger import (
    log_cl_communication_event,
)
from cases.case2.src.stack.cl_application import ClSampleMessage


_cl_sent_sample_count = 0


class ClUserBehavior(AbstractBehavior):
    @staticmethod
    async def send_training_samples(entity, data):
        if not entity.access_satellite:
            return
        if "*" not in entity.mac_table:
            return

        dataset = data["train_dataset"]
        train_indices = data["train_indices"]
        server_ip_address = data["server_ip_address"]
        samples_per_message = data["samples_per_message"]

        for _ in range(samples_per_message):
            sample_local_index = get_next_sample_local_index(
                entity=entity,
                dataset_size=len(dataset),
            )
            image, label = dataset[sample_local_index]
            sample_original_index = get_original_sample_index(
                train_indices=train_indices,
                sample_local_index=sample_local_index,
            )
            sample_message = ClSampleMessage(
                image=image,
                label=int(label),
                index=sample_original_index,
            )
            await send_sample_message(
                entity=entity,
                sample_message=sample_message,
                server_ip_address=server_ip_address,
            )


def get_next_sample_local_index(entity, dataset_size):
    from configuration import simulation_config as cg

    if dataset_size <= 0:
        raise ValueError("CL training dataset cannot be empty.")
    if not hasattr(entity, "case2_cl_sample_cursor"):
        entity.case2_cl_sample_cursor = 0
    sample_index = (
        entity.entity_id
        + entity.case2_cl_sample_cursor * cg.USER_NUMBER
    ) % dataset_size
    entity.case2_cl_sample_cursor += 1
    return int(sample_index)


def get_original_sample_index(train_indices, sample_local_index):
    if train_indices is None:
        return int(sample_local_index)
    return int(train_indices[sample_local_index])


async def send_sample_message(entity, sample_message, server_ip_address):
    from configuration import simulation_config as cg

    payload = ClSampleMessage.data_to(sample_message)
    payload_byte = len(payload)
    network_counted_byte = int(round(payload_byte * cg.ML_DATA_SIZE_SCALING))
    next_hop_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
    data_others = {
        "source_port": cg.CASE2_APPLICATION_PORT,
        "target_port": cg.CASE2_APPLICATION_PORT,
        "source_ip": entity.ip_address,
        "target_ip": server_ip_address,
        "next_hop_ip": next_hop_ip,
        "data_size_byte": network_counted_byte,
        "delay": 0,
        "path": None,
        "ip_list": None,
    }
    cross_layer_message = CrossLayerMessage(
        action=ActionType.ENCAPSULATE,
        cross_layer_interface=cg.CASE2_APPLICATION_PORT,
        data=sample_message,
        data_others=data_others,
    )
    cross_layer_message = StackFunc.encapsulate_message_to_signal(
        entity=entity,
        cross_layer_message=cross_layer_message,
    )
    if cross_layer_message is None:
        return

    cross_layer_message.data_others["path"] = deque()
    cross_layer_message.data_others["path"].append(entity.position_3D)
    cross_layer_message.data_others["ip_list"] = deque()
    cross_layer_message.data_others["ip_list"].append(entity.ip_address)
    buffer = entity.mac_table["*"]["Default"]
    await buffer.put(cross_layer_message)
    NetworkPerformance.packet_generate(data_size_byte=network_counted_byte)
    record_sample_sent_checkpoint(
        entity=entity,
        sample_message=sample_message,
        target_ip=server_ip_address,
        payload_byte=payload_byte,
        network_counted_byte=network_counted_byte,
    )
    return


def record_sample_sent_checkpoint(entity, sample_message, target_ip,
                                  payload_byte, network_counted_byte):
    global _cl_sent_sample_count
    from configuration import simulation_config as cg

    _cl_sent_sample_count += 1
    if not should_log_checkpoint(_cl_sent_sample_count,
                                 cg.CL_COMMUNICATION_LOG_INTERVAL):
        return

    log_cl_communication_event(
        simulation_time=get_current_time(entity=entity),
        event_type="sample_sent_checkpoint",
        cumulative_samples=_cl_sent_sample_count,
        entity_id=entity.entity_id,
        source_ip=entity.ip_address,
        target_ip=target_ip,
        sample_index=sample_message.index,
        label=sample_message.label,
        payload_byte=payload_byte,
        network_counted_byte=network_counted_byte,
    )
    return


def should_log_checkpoint(count, interval):
    return count == 1 or (interval > 0 and count % interval == 0)


def get_current_time(entity):
    if hasattr(entity, "current_time"):
        return float(entity.current_time[0])
    return 0.0
