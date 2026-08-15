from collections import deque

from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore

from cases.case2.experiment.integration.case2_event_logger import (
    log_fl_communication_event,
)
from cases.case2.experiment.learning.cnn_model import build_simple_cnn
from cases.case2.experiment.learning.cnn_model import require_torch
from cases.case2.src.stack.fl_application import FL_MESSAGE_TYPE_UPDATE
from cases.case2.src.stack.fl_application import FlModelMessage
from cases.case2.src.stack.fl_application import build_fl_model_messages
from cases.case2.src.stack.fl_application import state_dict_to_bytes


class FlUserBehavior(AbstractBehavior):
    @staticmethod
    def train_local_model(entity, data):
        round_id = getattr(entity, "case2_fl_pending_round_id", None)
        if round_id is None:
            return
        if round_id <= getattr(entity, "case2_fl_trained_round_id", 0):
            return

        global_state_dict = getattr(entity, "case2_fl_global_state_dict", None)
        if global_state_dict is None:
            return

        train_dataset = data["train_dataset"]
        user_partition_indices = data["user_partition_indices"][entity.entity_id]
        state_dict = train_user_model(
            train_dataset=train_dataset,
            user_partition_indices=user_partition_indices,
            global_state_dict=global_state_dict,
        )
        entity.case2_fl_local_state_dict = state_dict
        entity.case2_fl_local_round_id = round_id
        entity.case2_fl_trained_round_id = round_id
        return

    @staticmethod
    async def send_model_update(entity, data):
        if not entity.access_satellite:
            return
        if "*" not in entity.mac_table:
            return

        local_state_dict = getattr(entity, "case2_fl_local_state_dict", None)
        if local_state_dict is None:
            return

        round_id = getattr(entity, "case2_fl_local_round_id", 0)
        if round_id <= getattr(entity, "case2_fl_update_sent_round_id", 0):
            return

        is_sent = await send_fl_update_message(
            entity=entity,
            state_dict=local_state_dict,
            round_id=round_id,
            server_ip_address=data["server_ip_address"],
        )
        if not is_sent:
            return
        entity.case2_fl_update_sent_round_id = round_id
        entity.case2_fl_local_state_dict = None
        return


def train_user_model(train_dataset, user_partition_indices, global_state_dict):
    from configuration import simulation_config as cg

    torch, nn = require_torch()
    import torch.optim as optim
    from torch.utils.data import DataLoader
    from torch.utils.data import Subset

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    local_model = build_simple_cnn(device=device)
    local_model.load_state_dict(global_state_dict)
    local_dataset = Subset(train_dataset, user_partition_indices)
    data_loader = DataLoader(
        local_dataset,
        batch_size=cg.ML_BATCH_SIZE,
        shuffle=True,
    )
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(local_model.parameters(), lr=cg.ML_LEARNING_RATE)

    local_model.train()
    for _ in range(cg.ML_LOCAL_EPOCHS):
        for batch_data, batch_target in data_loader:
            batch_data = batch_data.to(device)
            batch_target = batch_target.to(device)
            optimizer.zero_grad()
            output = local_model(batch_data)
            loss = criterion(output, batch_target)
            loss.backward()
            optimizer.step()

    return {
        name: value.detach().cpu()
        for name, value in local_model.state_dict().items()
    }


async def send_fl_update_message(entity, state_dict, round_id,
                                 server_ip_address):
    from configuration import simulation_config as cg

    state_dict_bytes = state_dict_to_bytes(state_dict)
    model_messages = build_fl_model_messages(
        parameters=state_dict_bytes,
        user_id=entity.entity_id,
        round_id=round_id,
        message_type=FL_MESSAGE_TYPE_UPDATE,
        chunk_payload_byte=cg.FL_CHUNK_PAYLOAD_BYTE,
    )
    total_network_counted_byte = 0
    next_hop_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
    buffer = entity.mac_table["*"]["Default"]

    for model_message in model_messages:
        payload_byte = len(FlModelMessage.data_to(model_message))
        network_counted_byte = int(round(
            payload_byte * cg.ML_DATA_SIZE_SCALING
        ))
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
            data=model_message,
            data_others=data_others,
        )
        cross_layer_message = StackFunc.encapsulate_message_to_signal(
            entity=entity,
            cross_layer_message=cross_layer_message,
        )
        if cross_layer_message is None:
            continue

        cross_layer_message.data_others["path"] = deque()
        cross_layer_message.data_others["path"].append(entity.position_3D)
        cross_layer_message.data_others["ip_list"] = deque()
        cross_layer_message.data_others["ip_list"].append(entity.ip_address)
        await buffer.put(cross_layer_message)
        NetworkPerformance.packet_generate(data_size_byte=network_counted_byte)
        total_network_counted_byte += network_counted_byte

    if total_network_counted_byte <= 0:
        return False

    log_fl_communication_event(
        simulation_time=get_current_time(entity=entity),
        event_type="local_update_sent",
        round_id=round_id,
        user_id=entity.entity_id,
        source_ip=entity.ip_address,
        target_ip=server_ip_address,
        payload_byte=len(state_dict_bytes),
        network_counted_byte=total_network_counted_byte,
    )
    return True


def get_current_time(entity):
    if hasattr(entity, "current_time"):
        return float(entity.current_time[0])
    return 0.0
