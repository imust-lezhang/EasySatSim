from src.abstract.manager.stack_manager import AbstractStackManager
from src.simulation.stack.protocol_data.application_data import DataMessage, AccessMessage
from src.simulation.stack.protocol_data.transport_data import DataSegment
from src.simulation.stack.protocol_data.network_data import DataPacket, NeighborInfo
from src.simulation.stack.protocol_data.link_data import DataFrame
from src.simulation.stack.protocol_data.physical_data import DataBinary
from src.simulation.stack.protocol_func.application_func import Port80, Port10001, Port20000
from src.simulation.stack.protocol_func.transport_func import Protocol0x0006
from src.simulation.stack.protocol_func.network_func import Type0x0800, Type0x9000
from src.simulation.stack.protocol_func.link_func import LinkEthernet
from src.simulation.stack.protocol_func.physical_func import PhyEthernet


class StackManager(AbstractStackManager):
    def __init__(self):
        super().__init__()

    def load_default_setting(self):
        self._load_default_data()
        self._load_default_func()
        self._load_default_relationship()
        return

    def _load_default_data(self):
        self.add_protocol_data(layer_name="application", data_name="data_message", data_type=DataMessage
                               , to_data_func=DataMessage.to_data, data_to_func=DataMessage.data_to)
        self.add_protocol_data(layer_name="application", data_name="access_message", data_type=AccessMessage
                               , to_data_func=AccessMessage.to_data, data_to_func=AccessMessage.data_to)
        self.add_protocol_data(layer_name="transport", data_name="data_segment", data_type=DataSegment
                               , to_data_func=DataSegment.to_data, data_to_func=DataSegment.data_to)
        self.add_protocol_data(layer_name="network", data_name="data_packet", data_type=DataPacket
                               , to_data_func=DataPacket.to_data, data_to_func=DataPacket.data_to)

        self.add_protocol_data(layer_name="network", data_name="neighbor_info", data_type=NeighborInfo
                               , to_data_func=NeighborInfo.to_data, data_to_func=NeighborInfo.data_to)

        self.add_protocol_data(layer_name="link", data_name="data_frame", data_type=DataFrame
                               , to_data_func=DataFrame.to_data, data_to_func=DataFrame.data_to)
        self.add_protocol_data(layer_name="physical", data_name="data_binary", data_type=DataBinary
                               , to_data_func=DataBinary.to_data, data_to_func=DataBinary.data_to)
        return

    def _load_default_func(self):
        self.add_protocol_func(layer_name="application", protocol_name=80, parse_func=Port80.parse_and_process_func
                               , encapsulate_func=Port80.encapsulate_func)
        self.add_protocol_func(layer_name="application", protocol_name=10001, parse_func=Port10001.parse_and_process_func
                               , encapsulate_func=Port10001.encapsulate_func)
        self.add_protocol_func(layer_name="transport", protocol_name=0x0006, parse_func=Protocol0x0006.parse_and_process_func
                               , encapsulate_func=Protocol0x0006.encapsulate_func)
        self.add_protocol_func(layer_name="network", protocol_name=0x0800, parse_func=Type0x0800.parse_and_process_func
                               , encapsulate_func=Type0x0800.encapsulate_func)


        self.add_protocol_func(layer_name="network", protocol_name=0x9000, parse_func=Type0x9000.parse_and_process_func
                               , encapsulate_func=Type0x9000.encapsulate_func)


        self.add_protocol_func(layer_name="link", protocol_name="Ethernet", parse_func=LinkEthernet.parse_and_process_func
                               , encapsulate_func=LinkEthernet.encapsulate_func)
        self.add_protocol_func(layer_name="physical", protocol_name="Ethernet", parse_func=PhyEthernet.parse_and_process_func
                               , encapsulate_func=PhyEthernet.encapsulate_func)
        return

    def _load_default_relationship(self):
        self.add_relationship(layer_name="application", protocol_name=80, data_name="data_message")
        self.add_relationship(layer_name="application", protocol_name=10001, data_name="access_message")
        self.add_relationship(layer_name="transport", protocol_name=0x0006, data_name="data_segment")
        self.add_relationship(layer_name="network", protocol_name=0x0800, data_name="data_packet")
        self.add_relationship(layer_name="network", protocol_name=0x9000, data_name="neighbor_info")
        self.add_relationship(layer_name="link", protocol_name="Ethernet", data_name="data_frame")
        self.add_relationship(layer_name="physical", protocol_name="Ethernet", data_name="data_binary")
        return

    def load_test_mode(self):
        self._load_default_data()
        self.add_protocol_func(layer_name="application", protocol_name=80, parse_func=Port80.parse_and_process_func
                              , encapsulate_func=Port80.encapsulate_func)
        self.add_protocol_func(layer_name="application", protocol_name=10001,
                               parse_func=Port10001.parse_and_process_func
                               , encapsulate_func=Port10001.encapsulate_func)
        self.add_protocol_func(layer_name="application", protocol_name=20000,
                               parse_func=Port20000.parse_and_process_func
                               , encapsulate_func=Port20000.encapsulate_func)

        self.add_protocol_func(layer_name="transport", protocol_name=0x0006,
                               parse_func=Protocol0x0006.parse_and_process_func
                               , encapsulate_func=Protocol0x0006.encapsulate_func)
        self.add_protocol_func(layer_name="network", protocol_name=0x0800, parse_func=Type0x0800.parse_and_process_func
                               , encapsulate_func=Type0x0800.encapsulate_func)

        self.add_protocol_func(layer_name="network", protocol_name=0x9000, parse_func=Type0x9000.parse_and_process_func
                               , encapsulate_func=Type0x9000.encapsulate_func)

        self.add_protocol_func(layer_name="link", protocol_name="Ethernet",
                               parse_func=LinkEthernet.parse_and_process_func
                               , encapsulate_func=LinkEthernet.encapsulate_func)
        self.add_protocol_func(layer_name="physical", protocol_name="Ethernet",
                               parse_func=PhyEthernet.parse_and_process_func
                               , encapsulate_func=PhyEthernet.encapsulate_func)

        self.add_relationship(layer_name="application", protocol_name=80, data_name="data_message")
        self.add_relationship(layer_name="application", protocol_name=20000, data_name="data_message")
        self.add_relationship(layer_name="application", protocol_name=10001, data_name="access_message")
        self.add_relationship(layer_name="transport", protocol_name=0x0006, data_name="data_segment")
        self.add_relationship(layer_name="network", protocol_name=0x0800, data_name="data_packet")

        self.add_relationship(layer_name="network", protocol_name=0x9000, data_name="neighbor_info")

        self.add_relationship(layer_name="link", protocol_name="Ethernet", data_name="data_frame")
        self.add_relationship(layer_name="physical", protocol_name="Ethernet", data_name="data_binary")


    def load_2000port(self):
        self.add_protocol_func(layer_name="application", protocol_name=20000,
                               parse_func=Port20000.parse_and_process_func
                               , encapsulate_func=Port20000.encapsulate_func)
        self.add_relationship(layer_name="application", protocol_name=20000, data_name="data_message")



    def register_routing_algorithm(self, routing_algorithm_func):
        Type0x0800.routing_algorithm_func = routing_algorithm_func
        return





