import logging
import polyinterface
from av_funcs import get_server_data

"""
polyinterface has a LOGGER that is created by default and logs to:
logs/debug.log
You can use LOGGER.info, LOGGER.warning, LOGGER.debug, LOGGER.error levels as needed.
"""
LOGGER = polyinterface.LOGGER

DEFAULT_SHORT_POLL = 10
DEFAULT_LONG_POLL = 30
DEFAULT_DEBUG_MODE = 0


class AVController(polyinterface.Controller):
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

    SUPPORTED_DEVICES = [
        "VSX1021"
    ]

    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        self.serverdata = get_server_data(LOGGER)
        self.l_info("init", "Initializing A/V NodeServer version %s" % str(self.serverdata["version"]))
        self.ready = False
        self.hb = 0
        self.debug_mode = DEFAULT_DEBUG_MODE
        self.short_poll = DEFAULT_SHORT_POLL
        self.long_poll = DEFAULT_LONG_POLL
        self.device_count = 0
        self._device_nodes = {}
        super(AVController, self).__init__(polyglot)
        self.name = "AV Controller"
        self.address = "avcontroller"
        self.primary = self.address
        self.discover()

    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        self.l_info("init", "Starting A/V NodeServer version %s" % str(self.serverdata["version"]))
        v = self.polyConfig["shortPoll"]
        if v is None or v == 0:
            self.polyConfig["shortPoll"] = self.short_poll
        else:
            self.short_poll = v

        self.long_poll = self.polyConfig["longPoll"]
        if v is None or v == 0:
            self.polyConfig["longPoll"] = self.long_poll
        else:
            self.long_poll = v

        self.load_params()
        self.discover()

    def load_params(self):
        v = self.getCustomParam("debugMode")
        if v is None:
            self.addCustomParam({"debugMode": self.debug_mode})
        else:
            self.debug_mode = v

        """
        Load device info for node creation from customParams.  Requires several keys to define a device node, i.e:
            VSX1021_0_HOST = 192.168.1.1
            VSX1021_0_PORT = 23
            VSX1021_1_HOST = 192.168.1.2
            VSX1021_1_PORT = 23
            ... up to 9
        """

        device_types = {}
        for device_type in self.SUPPORTED_DEVICES:
            devices = {}
            for i in range(0, 9):
                device = "{}_{}".format(device_type, i)
                host = self.getCustomParam(device + "_HOST")
                if host is None:
                    continue

                port = self.getCustomParam(device + "_PORT")
                if port is None:
                    self.l_error("load_params", device_type + "_PORT key missing: ignoring")
                    continue

                sv = host.split(".")
                if len(sv) != 4:
                    self.l_error("load_params", "Invalid host IP")
                    continue

                suffix = "_{}_{}_{}".format(i, sv[3], port)
                prefix = device_type[0:14-len(suffix)]
                address = prefix + suffix
                device = {
                    address: {
                        "host": host,
                        "port": port
                    }
                }

                devices.update(device)
                self.l_debug("load_params", "Node Added: {}, Address: {}, Host: {}, Port: {}"
                             .format(device_type, address, device[address]["host"], device[address]["port"]))

            device_types.update({device_type: devices})

        self._device_nodes = device_types
        self.l_info("load_params", "{} devices supported".format(len(self._device_nodes)))
        for dt_k, dt_v in self._device_nodes.items():
            self.l_info("load_params", dt_k)
            for d_k, d_v in dt_v.items():
                self.l_debug("load_params", "{}: Address: {}, Host: {}, Port: {}"
                             .format(dt_k, d_k, d_v["host"], d_v["port"]))

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        if not self.ready:
            # Debug mode
            self.setDriver("GV6", self.debug_mode)

            # Short Poll
            v = self.getDriver("GV4")
            if v is None or int(v) == 0:
                v = self.polyConfig["shortPoll"]
            self.set_short_poll(v)

            # Long Poll
            v = self.getDriver("G5")
            if v is None or int(v) == 0:
                v = self.polyConfig["longPoll"]
            self.set_long_poll(v)

            self.query()
            self.ready = True
            self.setDriver("ST", 1)

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overridden in the server.json.
        """
        self.heartbeat()

    def heartbeat(self):
        self.l_debug("heartbeat", "hb={}".format(self.hb))
        if self.hb is None or self.hb == 0:
            self.reportCmd("DON", 2)
            self.hb = 1
        else:
            self.reportCmd("DOF", 2)
            self.hb = 0
        self.setDriver("GV7", self.hb)

    def query(self):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        self.setDriver("GV3", len(self._device_nodes))
        self.setDriver("GV1", self.serverdata["version_major"])
        self.setDriver("GV2", self.serverdata["version_minor"])

        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command received from ISY as an exmaple.
        """
        cnt = 0
        for dt_v in self._device_nodes.values():
            cnt += len(dt_v)

        self.l_debug("discover", "Cnt = {}".format(cnt))
        self.set_device_count(cnt)
#        self.addNode(MyNode(self, self.address, 'myaddress', 'My Node Name'))

    def delete(self):
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminated within 5 seconds
        of receiving this message.
        """
        LOGGER.info("Oh God I\"m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.")

    def stop(self):
        LOGGER.debug("A/V NodeServer stopped.")

    def remove_notices_all(self, command):
        LOGGER.info("remove_notices_all:")
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self, command):
        LOGGER.info("update_profile:")
        st = self.poly.installprofile()
        return st

    def set_device_count(self, count):
        self.device_count = count
        self.setDriver("GV3", self.device_count)

    @classmethod
    def set_all_logs(cls, level):
        LOGGER.setLevel(level)
        logging.getLogger("av_receiver").setLevel(level)
#        logging.getLogger("requests").setLevel(level)
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
        self.setDriver("GV6", level)
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

    def set_short_poll(self, val):
        if val is None or int(val) < 10:
            val = 10
        self.short_poll = int(val)
        self.setDriver("GV4", self.short_poll)
        self.polyConfig["shortPoll"] = self.short_poll

    def set_long_poll(self, val):
        if val is None:
            val = 300
        if int(val) > 300:
            val = 300
        self.long_poll = int(val)
        self.setDriver("GV5", self.long_poll)
        self.polyConfig["longPoll"] = self.long_poll

    """
    Command Functions
    """
    def cmd_set_debug_mode(self, command):
        val = command.get("value")
        self.l_info("cmd_set_debug_mode", val)
        self.set_debug_mode(val)

    def cmd_set_short_poll(self, command):
        val = command.get("value")
        self.l_info("cmd_set_short_poll", val)
        self.set_short_poll(val)

    def cmd_set_long_poll(self, command):
        val = int(command.get("value"))
        self.l_info("cmd_set_long_poll", val)
        self.set_long_poll(val)

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
        "SET_SHORTPOLL": cmd_set_short_poll,
        "SET_LONGPOLL":  cmd_set_long_poll,
        "DISCOVER": discover,
        "UPDATE_PROFILE": update_profile,
        "REMOVE_NOTICES_ALL": remove_notices_all
    }
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 56},   # vmaj: Version Major
        {"driver": "GV2", "value": 0, "uom": 56},   # vmin: Version Minor
        {"driver": "GV3", "value": 0, "uom": 56},   # device count
        {"driver": "GV4", "value": DEFAULT_SHORT_POLL, "uom": 56},  # shortpoll
        {"driver": "GV5", "value": DEFAULT_LONG_POLL, "uom": 56},  # longpoll
        {"driver": "GV7", "value": 0, "uom": 25},   # heartbeat
        {"driver": "GV6", "value": DEFAULT_DEBUG_MODE, "uom": 25}    # Debug (Log) Mode
    ]


class MyNode(polyinterface.Node):
    """
    This is the class that all the Nodes will be represented by. You will add this to
    Polyglot/ISY with the controller.addNode method.

    Class Variables:
    self.primary: String address of the Controller node.
    self.parent: Easy access to the Controller Class from the node itself.
    self.address: String address of this Node 14 character limit. (ISY limitation)
    self.added: Boolean Confirmed added to ISY

    Class Methods:
    start(): This method is called once polyglot confirms the node is added to ISY.
    setDriver('ST', 1, report = True, force = False):
        This sets the driver 'ST' to 1. If report is False we do not report it to
        Polyglot/ISY. If force is True, we send a report even if the value hasn't changed.
    reportDrivers(): Forces a full update of all drivers to Polyglot/ISY.
    query(): Called when ISY sends a query request to Polyglot for this specific node
    """
    def __init__(self, controller, primary, address, name):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """
        super(MyNode, self).__init__(controller, primary, address, name)

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        self.setDriver('ST', 1)
        pass

    def set_on(self, command):
        """
        Example command received from ISY.
        Set DON on MyNode.
        Sets the ST (status) driver to 1 or 'True'
        """
        self.setDriver('ST', 1)

    def set_off(self, command):
        """
        Example command received from ISY.
        Set DOF on MyNode
        Sets the ST (status) driver to 0 or 'False'
        """
        self.setDriver('ST', 0)

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    """
    Optional.
    This is an array of dictionary items containing the variable names(drivers)
    values and uoms(units of measure) from ISY. This is how ISY knows what kind
    of variable to display. Check the UOM's in the WSDK for a complete list.
    UOM 2 is boolean so the ISY will display 'True/False'
    """
    id = "mynodetype"
    """
    id of the node from the nodedefs.xml that is in the profile.zip. This tells
    the ISY what fields and commands this node has.
    """
    commands = {
        "DON": set_on,
        "DOF": set_off
    }
    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls set_on, etc.
    """
