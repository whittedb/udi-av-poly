import logging
import polyinterface
import os
import asyncore
from copy import deepcopy, copy
from threading import Thread
from av_funcs import get_server_data, get_profile_info
from nodes.node_factory import NodeFactory

"""
polyinterface has a LOGGER that is created by default and logs to:
logs/debug.log
You can use LOGGER.info, LOGGER.warning, LOGGER.debug, LOGGER.error levels as needed.
"""
LOGGER = polyinterface.LOGGER

DEFAULT_SHORT_POLL = 10
DEFAULT_LONG_POLL = 30
DEFAULT_DEBUG_MODE = 0


class AVController(polyinterface.Controller, NodeFactory.SsdpListener):
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
    self.added: Boolean Confirmed added to ISY as primary node
    self.config: Dictionary, this node's Config

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node, update = False): Adds Node to self.nodes and polyglot/ISY. This is called
        for you on the controller itself. Update = True overwrites the existing Node data.
    updateNode(polyinterface.Node): Overwrites the existing node data here and on Polyglot.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    getDriver('ST'): gets the current value from Polyglot for driver 'ST' returns a STRING, cast as needed
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """

    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        self.ready = False
        self.serverData = get_server_data(LOGGER)
        self.l_info("init", "Initializing A/V NodeServer version %s" % str(self.serverData["version"]))
        self.hb = 0
        self.profile_info = None
        self.update_profile = False
        self.debug_mode = DEFAULT_DEBUG_MODE
        super().__init__(polyglot)
        self.name = "AV Controller"
        self.primary = self.address
        self._nodeFactory = NodeFactory(self, self)
        self._stopAsyncLoop = False
        self._asyncStop = AsyncoreStop(self._stopAsyncLoop)
        self._asyncoreThread = Thread(name="AV Async Core", target=self._asyncore_loop)

    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        self.l_info("init", "Starting A/V NodeServer version %s" % str(self.serverData["version"]))
        self._nodeFactory.start_ssdp_listener()
        self.check_profile()

        self.setDriver("GV1", self.serverData["version_major"])
        self.setDriver("GV2", self.serverData["version_minor"])
        self.setDriver("GV6", self.debug_mode)

        self.setDriver("ST", 1)
        self.reportDrivers()

        self._asyncoreThread.start()
        self.discover()

    def discover(self, *args, **kwargs):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command received from ISY as an exmaple.
        """
        if not self.ready:
            self.add_config_devices()
            device_nodes = self.get_device_nodes()
            self.l_debug("discover", "Existing Node Count = {}".format(len(device_nodes)))

        # Add missing nodes
        param_devices = self._nodeFactory.load_params()
        self.l_debug("discover", "Parameter Device Count = {}".format(len(param_devices)))
        for k, v in param_devices.items():
            if k not in self.nodes:
                self.add_node(address=k, device_type=v["type"], name=v["name"], host=v["host"], port=v["port"])

        self.set_device_count(len(self.get_device_nodes()))

        self._nodeFactory.ssdp_search()
        self.ready = True

    def on_new_ssdp_node(self, node):
        if node.address not in self.nodes:
            self.l_debug("on_new_ssdp_node", "Adding new node")
            self.l_debug("on_new_ssdp_node", node)
            self.addNode(node)
            self.set_device_count(len(self.get_device_nodes()))

    def add_config_devices(self):
        """
        Called on startup to add the devices from the config
        """
        config_nodes = self.get_config_nodes()
        self.l_debug("add_config_devices", "{} existing nodes to add".format(len(config_nodes)))
        for node in config_nodes.values():
            if node["address"] not in self.nodes:
                self.add_config_node(node)

    def check_profile(self):
        self.profile_info = get_profile_info(LOGGER)
        
        # Set Default profile version if not Found
        cd = deepcopy(self.polyConfig["customData"])
        self.l_info("check_profile", "profile_info={0} customData={1}".format(self.profile_info, cd))
        if "profile_info" not in cd:
            cd["profile_info"] = {"version": 0}
        if self.profile_info["version"] == cd["profile_info"]["version"]:
            self.update_profile = False
        else:
            self.update_profile = True
            self.poly.installprofile()
        self.l_info("check_profile", "update_profile={}".format(self.update_profile))
        cd["profile_info"] = self.profile_info
        self.saveCustomData(cd)

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        pass

    def longPoll(self):
        """
        Optional.
        This runs every 60 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overridden in the server.json.
        """
        self.heartbeat()

    def heartbeat(self):
        if self.hb is None or self.hb == 0:
            self.hb = 1
        else:
            self.hb = 0
        self.setDriver("GV4", self.hb)

    def query(self):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        super().query()

    def delete(self):
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminated within 5 seconds
        of receiving this message.
        """
        LOGGER.info("Oh God I\"m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.")

    def stop(self):
        self._asyncStop.stop()
        self._asyncoreThread.join()
        for n in self.get_device_nodes().values():
            n.stop()
        self._nodeFactory.shutdown_ssdp_listener()

        LOGGER.debug("A/V NodeServer stopped.")

    def remove_notices_all(self, command):
        LOGGER.info("remove_notices_all:")
        # Remove all existing notices
        self.removeNoticesAll()

    def cmd_install_profile(self, command):
        LOGGER.info("cmd_install_profile:")
        st = self.poly.installprofile()
        return st

    def set_device_count(self, count):
        self.setDriver("GV3", count)

    def get_device_nodes(self):
        return {k: v for k, v in self.nodes.items() if v.address != "controller"}

    def get_config_nodes(self):
        return {k: v for k, v in self._nodes.items() if v["address"] != "controller"}

    def add_node(self, address, device_type, name, host, port):
        """
        Add a node that doesn't exist in either the config or controller
        :param address:
        :param device_type:
        :param name:
        :param host:
        :param port:
        :return:
        """
        node = self._nodeFactory.build(address=address, device_type=device_type, name=name, host=host, port=port)
        if node is not None:
            self.l_debug("add_node", "Adding node: {}, Address: {}, Host: {}, Port: {}"
                         .format(node.name, node.address, node.host, node.port))
            self.addNode(node)

        return node

    def add_config_node(self, node):
        """
        Add a node that exists in the config but not the controller if it has custom data
        :param node:
        :return:
        """
        address = node["address"]
        host = "{:d}.{:d}.{:d}.{:d}".format(
                self.hextoint(address[0:2]), self.hextoint(address[2:4]),
                self.hextoint(address[4:6]), self.hextoint(address[6:8]))
        port = "{:d}".format(self.hextoint(address[-4:]))
        LOGGER.debug("Building Node: address={}, type={}, name={}, host={}, port={}".format(
                address, node["node_def_id"], node["name"], host, port))
        new_node = self._nodeFactory.build(
                address=address, device_type=node["node_def_id"], name=node["name"], host=host, port=port)

        if new_node is not None:
            self.l_debug("add_existing_devices", "Adding existing: {}, Address: {}, Host: {}, Port: {}"
                         .format(new_node.name, new_node.address, new_node.host, new_node.port))
            self.addNode(new_node)

    @staticmethod
    def hextoint(s):
        return int(s, 16)

    def delete_node(self, address):
        cd = deepcopy(self.polyConfig["customData"])

        LOGGER.debug(cd)
        cd["node_data"].pop(address)
        self.saveCustomData(cd)
        LOGGER.debug(cd)
        self.delNode(address)

    def update_custom_node_data(self, node):
        cd = deepcopy(self.polyConfig["customData"])
        if "node_data" not in cd:
            node_data = {}
            cd["node_data"] = node_data
        else:
            node_data = cd["node_data"]

        node_data.update({node.address: {
                    "type": node.TYPE,
                    "name": node.name,
                    "host": node.host,
                    "port": node.port
                }
        })
        self.saveCustomData(cd)

    def get_custom_node_data(self, address):
        node_data = self.polyConfig["customData"]["node_data"]
        return node_data.get(address)

    @classmethod
    def set_all_logs(cls, level):
        LOGGER.setLevel(level)
        logging.getLogger("av_device").setLevel(level)
        logging.getLogger("transitions").setLevel(level)
#        logging.getLogger("urllib3").setLevel(level)

    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" % (self.id, name, string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.id, name, string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id, name, string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id, name, string))

    def set_debug_mode(self, level):
        if level is None:
            level = 0
        else:
            level = int(level)
        self.debug_mode = level
        self.addCustomParam({"debugMode": self.debug_mode})
        self.setDriver("GV5", level)
        # 0=All 10=Debug are the same because 0 (NOTSET) doesn't show everything.
        if level == 0 or level == 10:
            self.set_all_logs(logging.DEBUG)
        elif level == 20:
            self.set_all_logs(logging.INFO)
        elif level == 30:
            self.set_all_logs(logging.WARNING)
        elif level == 40:
            self.set_all_logs(logging.ERROR)
        elif level == 50:
            self.set_all_logs(logging.CRITICAL)
        else:
            self.l_error("set_debug_level", "Unknown level {0}".format(level))

    """
    Command Functions
    """
    def cmd_set_debug_mode(self, command):
        val = command.get("value")
        self.l_info("cmd_set_debug_mode", val)
        self.set_debug_mode(val)

    def _asyncore_loop(self):
        self.l_info("_asyncore_loop", "Starting asyncore loop thread")
        while True:
            try:
                asyncore.loop(2, True)
            except asyncore.ExitNow:
                for channel in copy(asyncore.socket_map).values():
                    channel.handle_close()
                break
        self.l_info("_asyncore_loop", "Ending asyncore loop thread")

    """
    Optional.
    Since the controller is the parent node in ISY, it will actual show up as a node.
    So it needs to know the drivers and what id it will use. The drivers are
    the defaults in the parent Class, so you don't need them unless you want to add to
    them. The ST and GV1 variables are for reporting status through Polyglot to ISY,
    DO NOT remove them. UOM 2 is boolean.
    """
    id = "avController"
    commands = {
        "SET_DM": cmd_set_debug_mode,
        "DISCOVER": discover,
        "UPDATE_PROFILE": cmd_install_profile,
        "REMOVE_NOTICES_ALL": remove_notices_all
    }
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 56},   # vmaj: Version Major
        {"driver": "GV2", "value": 0, "uom": 56},   # vmin: Version Minor
        {"driver": "GV3", "value": 0, "uom": 56},   # device count
        {"driver": "GV4", "value": 0, "uom": 25},   # heartbeat
        {"driver": "GV5", "value": DEFAULT_DEBUG_MODE, "uom": 25}    # Debug (Log) Mode
    ]


class AsyncoreStop(asyncore.file_dispatcher):
    def __init__(self, event_to_raise):
        self._eventToRaise = event_to_raise
        self._in_fd, self._out_fd = os.pipe()
        self._pipe = asyncore.file_wrapper(self._in_fd)
        super().__init__(self._pipe)

    def writable(self):
        return False

    def handle_close(self):
        os.close(self._out_fd)
        super().close()

    def handle_read(self):
        self.recv(64)
        self.handle_close()
        raise asyncore.ExitNow("Signal asyncore loop to exit")

    def stop(self):
        os.write(self._out_fd, b"stop")
