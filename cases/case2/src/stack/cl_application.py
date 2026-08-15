from dataclasses import dataclass

import numpy as np
import torch

from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


CL_IMAGE_SHAPE = (3, 32, 32)


@dataclass
class ClSampleMessage:
    image: torch.Tensor
    label: int
    index: int

    @staticmethod
    def data_to(this_layer_data):
        byte_mode = get_cl_sample_byte_mode()
        if byte_mode == "uint8_image":
            image_byte = normalized_tensor_to_uint8(this_layer_data.image)
            image_data = image_byte.numpy().tobytes()
        elif byte_mode == "float32_tensor":
            image_data = tensor_to_float32_bytes(this_layer_data.image)
        else:
            raise ValueError(f"Unsupported CL_SAMPLE_BYTE_MODE: {byte_mode}")

        label_data = str(int(this_layer_data.label)).encode("utf-8")
        index_data = int(this_layer_data.index).to_bytes(4, byteorder="big")
        return image_data + label_data + index_data

    @staticmethod
    def to_data(cross_layer_data):
        byte_mode = get_cl_sample_byte_mode()
        image_byte_size = get_cl_image_byte_size(byte_mode=byte_mode)
        image_data = cross_layer_data[:image_byte_size]
        label_data = cross_layer_data[image_byte_size:-4]
        index_data = cross_layer_data[-4:]

        if byte_mode == "uint8_image":
            image_array = np.frombuffer(
                image_data,
                dtype=np.uint8,
            ).reshape(CL_IMAGE_SHAPE)
            image_tensor = uint8_to_normalized_tensor(image_array)
        elif byte_mode == "float32_tensor":
            image_tensor = float32_bytes_to_tensor(image_data=image_data)
        else:
            raise ValueError(f"Unsupported CL_SAMPLE_BYTE_MODE: {byte_mode}")

        label = int(label_data.decode("utf-8"))
        index = int.from_bytes(index_data, byteorder="big")
        return ClSampleMessage(image=image_tensor, label=label, index=index)


class Port2024(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        sample_message = cross_layer_message.data
        source_ip = get_source_ip(cross_layer_message=cross_layer_message)
        source_user_id = VirtualStore.user_ip_to_id_table.get(source_ip, "")

        if hasattr(entity, "receive_cl_sample"):
            entity.receive_cl_sample(
                sample_message=sample_message,
                source_user_id=source_user_id,
                source_ip=source_ip,
                target_ip=entity.ip_address,
                payload_byte=len(ClSampleMessage.data_to(sample_message)),
                network_counted_byte=cross_layer_message.data_others[
                    "data_size_byte"
                ],
            )

        NetworkPerformance.packet_arrive(
            data_size_byte=cross_layer_message.data_others["data_size_byte"],
            total_delay=cross_layer_message.data_others["delay"],
            hop_count=len(cross_layer_message.data_others["path"]) - 2,
        )
        if entity.entity_id == 0:
            entity.set_routing_path(path_list=cross_layer_message.data_others["path"])
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message


def normalized_tensor_to_uint8(image):
    image = image.detach().cpu()
    restored_unit_image = image.mul(0.5).add(0.5)
    return restored_unit_image.mul(255).add(0.5).clamp(0, 255).to(torch.uint8)


def uint8_to_normalized_tensor(image_array):
    image_tensor = torch.from_numpy(image_array.copy()).float().div(255.0)
    return image_tensor.sub(0.5).div(0.5)


def tensor_to_float32_bytes(image):
    image_tensor = image.detach().cpu().contiguous().to(torch.float32)
    return image_tensor.numpy().tobytes()


def float32_bytes_to_tensor(image_data):
    image_array = np.frombuffer(
        image_data,
        dtype=np.float32,
    ).reshape(CL_IMAGE_SHAPE)
    return torch.from_numpy(image_array.copy()).float()


def get_cl_image_byte_size(byte_mode):
    if byte_mode == "uint8_image":
        return int(np.prod(CL_IMAGE_SHAPE))
    if byte_mode == "float32_tensor":
        return int(np.prod(CL_IMAGE_SHAPE)) * np.dtype(np.float32).itemsize
    raise ValueError(f"Unsupported CL_SAMPLE_BYTE_MODE: {byte_mode}")


def get_cl_sample_byte_mode():
    from configuration import simulation_config as cg

    byte_mode = getattr(cg, "CL_SAMPLE_BYTE_MODE", "uint8_image")
    return str(byte_mode).lower()


def get_source_ip(cross_layer_message):
    source_ip = cross_layer_message.data_others.get("source_ip")
    if source_ip:
        return source_ip

    ip_list = cross_layer_message.data_others.get("ip_list")
    if ip_list is not None and len(ip_list) > 0:
        return ip_list[0]
    return ""


def register_cl_application(stack_manager):
    from configuration import simulation_config as cg

    stack_manager.add_protocol_data(
        layer_name="application",
        data_name="case2_cl_sample",
        data_type=ClSampleMessage,
        to_data_func=ClSampleMessage.to_data,
        data_to_func=ClSampleMessage.data_to,
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
        data_name="case2_cl_sample",
    )
    return
