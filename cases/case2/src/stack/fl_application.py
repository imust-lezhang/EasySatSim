import io
import struct
from dataclasses import dataclass

import torch

from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


FL_MESSAGE_TYPE_UPDATE = 1
FL_MESSAGE_TYPE_GLOBAL = 2
FL_HEADER_FORMAT = ">iiiiii"
FL_HEADER_BYTE_SIZE = struct.calcsize(FL_HEADER_FORMAT)


@dataclass
class FlModelMessage:
    parameters: bytes
    user_id: int
    round_id: int
    message_type: int
    chunk_id: int = 0
    chunk_count: int = 1
    full_payload_byte: int = 0

    @staticmethod
    def data_to(this_layer_data):
        full_payload_byte = this_layer_data.full_payload_byte
        if full_payload_byte <= 0:
            full_payload_byte = len(this_layer_data.parameters)
        header = struct.pack(
            FL_HEADER_FORMAT,
            int(this_layer_data.user_id),
            int(this_layer_data.round_id),
            int(this_layer_data.message_type),
            int(this_layer_data.chunk_id),
            int(this_layer_data.chunk_count),
            int(full_payload_byte),
        )
        return header + this_layer_data.parameters

    @staticmethod
    def to_data(cross_layer_data):
        (user_id, round_id, message_type, chunk_id, chunk_count,
         full_payload_byte) = struct.unpack(
            FL_HEADER_FORMAT,
            cross_layer_data[:FL_HEADER_BYTE_SIZE],
        )
        parameters = cross_layer_data[FL_HEADER_BYTE_SIZE:]
        return FlModelMessage(
            parameters=parameters,
            user_id=user_id,
            round_id=round_id,
            message_type=message_type,
            chunk_id=chunk_id,
            chunk_count=chunk_count,
            full_payload_byte=full_payload_byte,
        )


class Port2024(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        model_message = cross_layer_message.data
        source_ip = get_source_ip(cross_layer_message=cross_layer_message)
        payload_byte = len(FlModelMessage.data_to(model_message))
        network_counted_byte = cross_layer_message.data_others["data_size_byte"]

        NetworkPerformance.packet_arrive(
            data_size_byte=network_counted_byte,
            total_delay=cross_layer_message.data_others["delay"],
            hop_count=len(cross_layer_message.data_others["path"]) - 2,
        )
        if entity.entity_id == 0:
            entity.set_routing_path(path_list=cross_layer_message.data_others["path"])

        transfer = collect_fl_model_chunk(
            entity=entity,
            model_message=model_message,
            source_ip=source_ip,
            payload_byte=payload_byte,
            network_counted_byte=network_counted_byte,
        )
        if transfer is None:
            cross_layer_message.action = ActionType.STOP
            return cross_layer_message

        complete_parameters, transfer_payload_byte, transfer_network_byte = transfer

        if model_message.message_type == FL_MESSAGE_TYPE_UPDATE:
            if hasattr(entity, "receive_fl_model_update"):
                state_dict = state_dict_from_bytes(complete_parameters)
                entity.receive_fl_model_update(
                    state_dict=state_dict,
                    user_id=model_message.user_id,
                    round_id=model_message.round_id,
                    source_ip=source_ip,
                    target_ip=entity.ip_address,
                    payload_byte=transfer_payload_byte,
                    network_counted_byte=transfer_network_byte,
                )
        elif model_message.message_type == FL_MESSAGE_TYPE_GLOBAL:
            receive_fl_global_model(
                entity=entity,
                model_message=model_message,
                source_ip=source_ip,
                payload_byte=transfer_payload_byte,
                network_counted_byte=transfer_network_byte,
                parameters=complete_parameters,
            )

        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message


def receive_fl_global_model(entity, model_message, source_ip,
                            payload_byte, network_counted_byte,
                            parameters):
    from cases.case2.experiment.integration.case2_event_logger import (
        log_fl_communication_event,
    )

    state_dict = state_dict_from_bytes(parameters)
    current_sent_round = getattr(entity, "case2_fl_update_sent_round_id", 0)
    if model_message.round_id <= current_sent_round:
        return

    entity.case2_fl_global_state_dict = state_dict
    entity.case2_fl_pending_round_id = model_message.round_id
    entity.case2_fl_pending_source_ip = source_ip
    log_fl_communication_event(
        simulation_time=get_current_time(entity=entity),
        event_type="global_model_received",
        round_id=model_message.round_id,
        user_id=entity.entity_id,
        source_ip=source_ip,
        target_ip=entity.ip_address,
        payload_byte=payload_byte,
        network_counted_byte=network_counted_byte,
    )
    return


def build_fl_model_messages(parameters, user_id, round_id, message_type,
                            chunk_payload_byte):
    chunk_payload_byte = int(chunk_payload_byte)
    if chunk_payload_byte <= 0:
        chunk_payload_byte = len(parameters)

    chunks = [
        parameters[start:start + chunk_payload_byte]
        for start in range(0, len(parameters), chunk_payload_byte)
    ]
    if not chunks:
        chunks = [b""]

    chunk_count = len(chunks)
    return [
        FlModelMessage(
            parameters=chunk,
            user_id=user_id,
            round_id=round_id,
            message_type=message_type,
            chunk_id=chunk_id,
            chunk_count=chunk_count,
            full_payload_byte=len(parameters),
        )
        for chunk_id, chunk in enumerate(chunks)
    ]


def collect_fl_model_chunk(entity, model_message, source_ip, payload_byte,
                           network_counted_byte):
    validate_model_chunk(model_message=model_message)
    if model_message.chunk_count == 1:
        transfer_payload_byte = model_message.full_payload_byte
        if transfer_payload_byte <= 0:
            transfer_payload_byte = len(model_message.parameters)
        return (
            model_message.parameters,
            transfer_payload_byte,
            network_counted_byte,
        )

    if not hasattr(entity, "case2_fl_chunk_buffers"):
        entity.case2_fl_chunk_buffers = {}

    key = get_chunk_buffer_key(
        model_message=model_message,
        source_ip=source_ip,
    )
    entry = entity.case2_fl_chunk_buffers.setdefault(
        key,
        {
            "chunk_count": model_message.chunk_count,
            "full_payload_byte": model_message.full_payload_byte,
            "chunks": {},
            "payload_byte": 0,
            "network_counted_byte": 0,
        },
    )
    if model_message.chunk_id in entry["chunks"]:
        return None

    entry["chunks"][model_message.chunk_id] = model_message.parameters
    entry["payload_byte"] += payload_byte
    entry["network_counted_byte"] += network_counted_byte

    if len(entry["chunks"]) < entry["chunk_count"]:
        return None

    complete_parameters = b"".join(
        entry["chunks"][chunk_id]
        for chunk_id in range(entry["chunk_count"])
    )
    del entity.case2_fl_chunk_buffers[key]

    if len(complete_parameters) != entry["full_payload_byte"]:
        raise ValueError(
            "Reassembled FL model payload size mismatch: "
            f"expected {entry['full_payload_byte']} bytes, "
            f"got {len(complete_parameters)} bytes."
        )
    return (
        complete_parameters,
        entry["full_payload_byte"],
        entry["network_counted_byte"],
    )


def validate_model_chunk(model_message):
    if model_message.chunk_count <= 0:
        raise ValueError("FL model chunk_count must be positive.")
    if not 0 <= model_message.chunk_id < model_message.chunk_count:
        raise ValueError(
            "FL model chunk_id must be in [0, chunk_count). "
            f"Got chunk_id={model_message.chunk_id}, "
            f"chunk_count={model_message.chunk_count}."
        )
    return


def get_chunk_buffer_key(model_message, source_ip):
    return (
        model_message.message_type,
        model_message.round_id,
        model_message.user_id,
        source_ip,
    )


def state_dict_to_bytes(state_dict):
    buffer = io.BytesIO()
    torch.save(state_dict, buffer)
    return buffer.getvalue()


def state_dict_from_bytes(parameters):
    buffer = io.BytesIO(parameters)
    try:
        return torch.load(buffer, map_location="cpu", weights_only=True)
    except TypeError:
        buffer.seek(0)
        return torch.load(buffer, map_location="cpu")


def get_source_ip(cross_layer_message):
    source_ip = cross_layer_message.data_others.get("source_ip")
    if source_ip:
        return source_ip

    ip_list = cross_layer_message.data_others.get("ip_list")
    if ip_list is not None and len(ip_list) > 0:
        return ip_list[0]
    return ""


def get_current_time(entity):
    if hasattr(entity, "current_time"):
        return float(entity.current_time[0])
    return 0.0


def register_fl_application(stack_manager):
    from configuration import simulation_config as cg

    stack_manager.add_protocol_data(
        layer_name="application",
        data_name="case2_fl_model",
        data_type=FlModelMessage,
        to_data_func=FlModelMessage.to_data,
        data_to_func=FlModelMessage.data_to,
    )
    stack_manager.add_protocol_func(
        layer_name="application",
        protocol_name=cg.CASE2_APPLICATION_PORT,
        parse_func=Port2024.parse_and_process_func,
        encapsulate_func=Port2024.encapsulate_func,
    )
    stack_manager.add_relationship(
        layer_name="application",
        protocol_name=cg.CASE2_APPLICATION_PORT,
        data_name="case2_fl_model",
    )
    return
