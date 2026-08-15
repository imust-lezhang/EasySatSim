from abc import ABC, abstractmethod


class AbstractStackManager(ABC):
    def __init__(self):
        self.__dict_protocol_data__ = {}  # Used to store all data types {layer: {name: {data type, to_data, data_to}}}
        self.__dict_protocol_func__ = {}  # Used to store all protocol stack functions {layer: {protocol type: {two functions}}}

        self.__dict_relationship_data_and_func = {}  # Used to store the corresponding relationship {layer: {interface: {encapsulation, parsing, to_data, data_to four functions}}}


    def add_protocol_data(self, layer_name, data_name, data_type, to_data_func, data_to_func):
        """
        Add a data type to the data dict
        :param layer_name: The name of the protocol stack layer where the data is located
        :param data_name: Data name
        :param data_type: The defined data type
        :param to_data_func: Function to convert data from other layers to this layer
        :param data_to_func: Function to convert data from this layer to other layers
        :return: None
        """
        if layer_name in self.__dict_protocol_data__:
            if data_name in self.__dict_protocol_data__[layer_name]:
                raise KeyError(f"[Wrong] Data '{data_name}' is already in __dict_protocol_data__.")
            else:
                self.__dict_protocol_data__[layer_name][data_name] = {"type":data_type, "to_data": to_data_func, "data_to": data_to_func}
        else:
            self.__dict_protocol_data__[layer_name] = {data_name: {"type":data_type, "to_data": to_data_func, "data_to": data_to_func}}


    def add_protocol_func(self, layer_name, protocol_name, parse_func, encapsulate_func, parse_data=None, encapsulate=None):
        """
        Add a protocol to the func dict
        :param layer_name: The name of the protocol stack layer where the protocol is located
        :param protocol_name: Protocol name
        :param parse_func: Parsing and processing function
        :param encapsulate_func: Encapsulation function
        :return: None
        """
        if layer_name in self.__dict_protocol_func__:
            if protocol_name in self.__dict_protocol_func__[layer_name]:
                raise KeyError(f"[Wrong] Protocol '{protocol_name}' is already in __dict_protocol_func__.")
            else:
                self.__dict_protocol_func__[layer_name][protocol_name] = {"parse": parse_func
                                                             , "encapsulate": encapsulate_func}
        else:
            self.__dict_protocol_func__[layer_name] = {protocol_name: {"parse": parse_func
                                                          , "encapsulate": encapsulate_func}}


    def replace_protocol_func(self, layer_name, protocol_name, parse_func, encapsulate_func):
        """Replace the handlers of an already registered protocol."""
        if layer_name not in self.__dict_protocol_func__:
            raise KeyError(
                f"[Wrong] Layer name '{layer_name}' not found in __dict_protocol_func__."
            )
        if protocol_name not in self.__dict_protocol_func__[layer_name]:
            raise KeyError(
                f"[Wrong] Protocol '{protocol_name}' not found in __dict_protocol_func__."
            )
        self.__dict_protocol_func__[layer_name][protocol_name] = {
            "parse": parse_func,
            "encapsulate": encapsulate_func,
        }


    def add_relationship(self, layer_name, protocol_name, data_name):
        if layer_name in self.__dict_protocol_func__ and layer_name in self.__dict_protocol_data__:
            if protocol_name in self.__dict_protocol_func__[layer_name] and data_name in self.__dict_protocol_data__[layer_name]:
                data_type = self.__dict_protocol_data__[layer_name][data_name]["type"]
                to_data_func = self.__dict_protocol_data__[layer_name][data_name]["to_data"]
                data_to_func = self.__dict_protocol_data__[layer_name][data_name]["data_to"]
                parse_func = self.__dict_protocol_func__[layer_name][protocol_name]["parse"]
                encapsulate_func = self.__dict_protocol_func__[layer_name][protocol_name]["encapsulate"]
                if layer_name not in self.__dict_relationship_data_and_func:
                    self.__dict_relationship_data_and_func[layer_name] = {protocol_name: {
                        "to_data": to_data_func, "data_to": data_to_func, "type": data_type
                       , "parse": parse_func, "encapsulate": encapsulate_func
                    }}
                else:
                    self.__dict_relationship_data_and_func[layer_name][protocol_name] = {
                        "to_data": to_data_func, "data_to": data_to_func, "type": data_type
                       , "parse": parse_func, "encapsulate": encapsulate_func
                    }
            else:
                raise KeyError(f"[Wrong] Protocol '{protocol_name}' not found in __dict_protocol_func__. or "
                             f"data '{data_name}' not found in __dict_protocol_data__. or ")
        else:
            raise KeyError(f"[Wrong] Layer name '{layer_name}' not found in __dict_protocol_func__ "
                         f"or __dict_protocol_data__.")


    def replace_relationship(self, layer_name, protocol_name, data_name):
        """Replace an existing protocol-data relationship without creating a new one."""
        if layer_name not in self.__dict_relationship_data_and_func:
            raise KeyError(
                f"[Wrong] Layer name '{layer_name}' not found in "
                "__dict_relationship_data_and_func."
            )
        if protocol_name not in self.__dict_relationship_data_and_func[layer_name]:
            raise KeyError(
                f"[Wrong] Protocol '{protocol_name}' not found in "
                "__dict_relationship_data_and_func."
            )
        self.add_relationship(
            layer_name=layer_name,
            protocol_name=protocol_name,
            data_name=data_name,
        )


    def get_parse_funcs(self, layer_name, protocol_name):
        parse_func = self.__dict_relationship_data_and_func[layer_name][protocol_name]["parse"]
        to_data_func = self.__dict_relationship_data_and_func[layer_name][protocol_name]["to_data"]
        return to_data_func, parse_func


    def get_encapsulate_funcs(self, layer_name, protocol_name):
        encapsulate_func = self.__dict_relationship_data_and_func[layer_name][protocol_name]["encapsulate"]
        data_to_func = self.__dict_relationship_data_and_func[layer_name][protocol_name]["data_to"]
        return data_to_func, encapsulate_func
