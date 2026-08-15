from src.abstract.stack.stack_process import AbstractStackProcess
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.manager.stack_manager import StackManager


# Protocol stack parsing
# Create data packets of different layers
class StackFunc(AbstractStackProcess):
    # Set the inter-layer order, using a list because it's ordered
    __layer_order__ = ["physical", "link", "network", "transport", "application"]  # From lower layer to upper layer, Physical-Link-Network-Transport-Application
    stack_manager = None


    @staticmethod
    def stack_processing(entity, cross_layer_message: CrossLayerMessage):
        # Build a cross-layer data packet
        cross_layer_message.action = ActionType.PARSE
        # Loop through each layer
        for layer_name in StackFunc.__layer_order__:
            # Get the parsing functions corresponding to the layer-protocol
            to_data_func, parse_func = StackFunc.stack_manager.get_parse_funcs(layer_name=layer_name
                                                                 , protocol_name=cross_layer_message.cross_layer_interface)
            # Convert the lower layer data to the current layer data
            cross_layer_message.data = to_data_func(cross_layer_data=cross_layer_message.data)
            encapsulate_interface = cross_layer_message.cross_layer_interface
            # Current layer processing
            cross_layer_message = parse_func(entity=entity, cross_layer_message=cross_layer_message)
            # Determine how to proceed next
            if cross_layer_message.action == ActionType.PARSE:
                # If the message returned by the current layer is to continue parsing, then continue looping
                continue
            elif cross_layer_message.action == ActionType.ENCAPSULATE:
                data_to_func, encapsulate_func = StackFunc.stack_manager.get_encapsulate_funcs(layer_name=layer_name
                                                                              , protocol_name=encapsulate_interface)
                cross_layer_message.data = data_to_func(this_layer_data=cross_layer_message.data)
                # If the returned message is encapsulation, then execute the encapsulation function
                cross_layer_message = StackFunc._encapsulate_layers(entity=entity, layers=reversed(StackFunc.__layer_order__[:StackFunc.__layer_order__.index(layer_name)])
                                                         , cross_layer_message=cross_layer_message)
                return cross_layer_message
            elif cross_layer_message.action == ActionType.STOP:
                # If the message returned by the current layer is to stop, it indicates that the data packet is only processed up to this layer
                return None
        layer_name = StackFunc.__layer_order__[-1]
        cross_layer_message = StackFunc._encapsulate_layers(entity=entity, layers=reversed(StackFunc.__layer_order__)
                                                   , cross_layer_message=cross_layer_message)
        return cross_layer_message


    @staticmethod
    def _encapsulate_layers(entity, layers, cross_layer_message):
        for layer_name in layers:
            # Get the encapsulation functions corresponding to the layer-protocol
            data_to_func, encapsulate_func = StackFunc.stack_manager.get_encapsulate_funcs(layer_name=layer_name
                                                                          , protocol_name=cross_layer_message.cross_layer_interface)
            cross_layer_message = encapsulate_func(entity=entity, cross_layer_message=cross_layer_message)
            if cross_layer_message.action == ActionType.ENCAPSULATE:
                cross_layer_message.data = data_to_func(this_layer_data=cross_layer_message.data)
                continue
            elif cross_layer_message.action == ActionType.STOP:
                return None
        return cross_layer_message


    @staticmethod
    def encapsulate_message_to_signal(entity, cross_layer_message):
        for layer_name in reversed(StackFunc.__layer_order__):
            # Get the encapsulation functions corresponding to the layer-protocol
            data_to_func, encapsulate_func = StackFunc.stack_manager.get_encapsulate_funcs(layer_name=layer_name,
                                                                           protocol_name=cross_layer_message.cross_layer_interface)
            cross_layer_message = encapsulate_func(entity=entity, cross_layer_message=cross_layer_message)
            if cross_layer_message.action == ActionType.ENCAPSULATE:
                cross_layer_message.data = data_to_func(this_layer_data=cross_layer_message.data)
                continue
            elif cross_layer_message.action == ActionType.STOP:
                return None
        return cross_layer_message


    @staticmethod
    def encapsulate_network_to_signal(entity, cross_layer_message):
        for layer_name in reversed(StackFunc.__layer_order__[0:3]):
            # Get the encapsulation functions corresponding to the layer-protocol
            data_to_func, encapsulate_func = StackFunc.stack_manager.get_encapsulate_funcs(layer_name=layer_name,
                                                                           protocol_name=cross_layer_message.cross_layer_interface)
            cross_layer_message = encapsulate_func(entity=entity, cross_layer_message=cross_layer_message)
            if cross_layer_message.action == ActionType.ENCAPSULATE:
                cross_layer_message.data = data_to_func(this_layer_data=cross_layer_message.data)
                continue
            elif cross_layer_message.action == ActionType.STOP:
                return None
        return cross_layer_message