import polyinterface
from copy import deepcopy
from ssdp.ssdp import SSDP
from .vsx1021_node import VSX1021Node

LOGGER = polyinterface.LOGGER


SUPPORTED_DEVICES = [
    "VSX1021"
]


class NodeFactory(SSDP.Listener):
    class SsdpListener(object):
        def on_new_ssdp_node(self, node):
            pass

    def __init__(self, controller, ssdp_listener=None):
        self._controller = controller
        self._primary = controller.address
        self._ssdpListeners = []
        self._ssdp = SSDP(self)

        if ssdp_listener is not None:
            self._ssdpListeners.append(ssdp_listener)

    def start_ssdp_listener(self):
        self._ssdp.start()

    def shutdown_ssdp_listener(self):
        self._ssdp.shutdown()

    def ssdp_search(self):
        self._ssdp.search("ssdp:all")

    def build(self, address=None, device_type=None, host=None, port=None, name=None):
        """
        Build new node.

        :param address:
        :param device_type: Device node to build unless "node" parameter is specified
        :param host:
        :param port:
        :param name:
        :return: new PolyGlot node
        """
        if device_type is None:
            LOGGER.error("device_type not specified for new node")
            return None

        if device_type == VSX1021Node.TYPE:
            return VSX1021Node(controller=self._controller, primary=self._primary,
                               address=address, host=host, port=port, name=name)

        return None

    def on_ssdp_response(self, ssdp_response):
        device_type = None
        if ssdp_response.manufacturer == "PIONEER CORPORATION" and "VSX-1021" in ssdp_response.model:
            device_type = VSX1021Node.TYPE
            ssdp_response.port = 23
            ssdp_response.model = device_type

        if device_type is not None:
            address = self.host_port_to_address(ssdp_response.host, ssdp_response.port)
            name = "{}_{}_{}".format(ssdp_response.model, ssdp_response.host, ssdp_response.port)
            node = self.build(address=address, device_type=device_type,
                              host=ssdp_response.host, port=ssdp_response.port, name=name)
            if node is not None:
                for l in self._ssdpListeners:
                    l.on_new_ssdp_node(node)

    def load_params(self):
        """
        Load device info for node creation from customParams.  Requires host IP:PORT
            VSX1021xxxx = 192.168.1.1:23

        Misc keys:
            debugMode:
                0, 10, 20, 30, 40, 50 (All, Debug, Info, Warning, Error, Critical)
        """

        v = self._controller.getCustomParam("debugMode")
        if v is None:
            self._controller.addCustomParam({"debugMode": self._controller.debug_mode})
        else:
            self._controller.debug_mode = v

        self._controller.l_info("load_params", "{} devices supported".format(len(SUPPORTED_DEVICES)))
        devices = {}
        for device_type in SUPPORTED_DEVICES:
            params = deepcopy(self._controller.polyConfig["customParams"])
            for k, v in params.items():
                if k.startswith(device_type):
                    host_port = v
                    name = device_type + "_" + host_port.replace(":", "_")

                    # Validate port exists in custom parameter value
                    sv = host_port.split(":")
                    if len(sv) != 2:
                        self._controller.l_error("load_params", "Invalid host IP specified - " + v)
                        continue

                    # Validate proper host IP format in custom parameter value
                    host = sv[0]
                    port = sv[1]
                    address = self.host_port_to_address(host, port)
                    if address is None:
                        self._controller.l_error("load_params", "Invalid host IP format - " + host_port)
                        continue

                    device = {
                        address: {
                            "type": device_type,
                            "name": name,
                            "address": address,
                            "host": host,
                            "port": port
                        }
                    }

                    devices.update(device)
                    self._controller.l_debug("load_params", "Param Node: {}, Address: {}, Host: {}, Port: {}".format(
                            device_type, address, device[address]["host"], device[address]["port"]))

        for k, v in devices.items():
            self._controller.l_debug("load_params", "{}: Address: {}, Host: {}, Port: {}".format(
                    v["type"], k, v["host"], v["port"]))

        return devices

    @staticmethod
    def host_port_to_address(host, port):
        sv = host.split(".")
        if len(sv) != 4:
            return None

        return "{:02x}{:02x}{:02x}{:02x}{:04x}".format(int(sv[0]), int(sv[1]), int(sv[2]), int(sv[3]), int(port))
