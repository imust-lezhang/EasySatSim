class VirtualStore:
    user_authentication_table = {}  # User authentication username and password table user_id:{'username': self.username, 'password': self.password}
    user_access_table = {}  # User access table in the format user_ip: satellite_ip


    # Store all buffers
    user_ip_to_id_table = {}  # user_ip: id
    satellite_ip_to_id_table = {}  # user_ip:id
    user_id_to_ip_table = {}  # user_id: ip
    satellite_id_to_ip_table = {}  # satellite_id:ip
    ip_to_mac_table = {}  # ip: mac
    mac_to_buffer_table = {}  # mac: buffer


    set_user_ip = None
    set_satellite_ip = None


    satellite_survival_state = {}  # id: bool


    @staticmethod
    def get_satellite_info_from_id(satellite_id):
        satellite_ip = VirtualStore.satellite_id_to_ip_table[satellite_id]
        satellite_mac = VirtualStore.ip_to_mac_table[satellite_ip]
        buffers = VirtualStore.mac_to_buffer_table[satellite_mac]
        return satellite_ip, satellite_mac, buffers