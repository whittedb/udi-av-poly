"""
This is a NodeServer for the Pioneer VSX-1021 A/V Receiver for Polyglot v2 written in Python3
by Brad Whitted brad_whitted@gmail.com
"""
import polyinterface
from av_receivers import VSX1021Client, AvReceiver

LOGGER = polyinterface.LOGGER


class AVDevice(polyinterface.Node):
    """
    This is the class that all the Nodes will be represented by.  You will add this to
    Polyglot/ISY with the controller.addNode method

    Class Variables:
    self.primary: String address of the Controller node.
    self.parent: Easy access to the Controller Class from the node itself
    self.address: String address of this Node. 14 character limit. (ISY limitation)
    self.added: Boolean confirmed added to ISY

    Class Methods:
    start(): This method is called once polyglot confirms the node is added to ISY.
    setDriver('ST', 1, report = True, force = False):
        This sets the driver 'ST' to 1.  If report is False we do not report it to
        Polyglot/ISY.  If force is True, we send a report even if the value hasn't changed.
    reportDrivers(): Forces a full update of all drivers to Polyglot/ISY.
        query(): Called when ISY sends a query request to Polyglot for this specific node
    """

    TYPE = "GENERIC"

    def __init__(self, controller, primary, address=None, name=None):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """

        LOGGER.debug("AVDevice:__init__: address={} name={} type={}".format(address, name, self.TYPE))
        self.id = self.TYPE
        super().__init__(controller, primary, address, name)

    def set_power(self, on_off):
        pass

    def set_mute(self, on_off):
        pass

    def set_volume(self, volume):
        pass

    def set_source(self, source):
        pass

    def l_info(self, name, string):
        LOGGER.info("%s: %s" % (name, string))

    def l_error(self, name, string):
        LOGGER.error("%s: %s" % (name, string))

    def l_warning(self, name, string):
        LOGGER.warning("%s: %s" % (name, string))

    def l_debug(self, name, string):
        LOGGER.debug("%s: %s" % (name, string))

    commands = {}
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 25},   # Device Type
        {"driver": "GV2", "value": 0, "uom": 25},   # Power
        {"driver": "GV3", "value": 0, "uom": 25},   # Mute
        {"driver": "GV4", "value": -80, "uom": 56},  # Volume
        {"driver": "GV5", "value": 999, "uom": 25}  # Input Source
    ]


class VSX1021Node(AVDevice, AvReceiver.Listener):
    TYPE = "VSX1021"

    def __init__(self, controller, primary, host, port, address=None, name=None):
        self.host = host
        self.port = port
        self.commands.update(self.my_commands)
        super().__init__(controller, primary, address, name)
        self.client = VSX1021Client(self.TYPE + ":" + name, self.host, self.port, logger=LOGGER)
        self.client.set_listener(self)

    def start(self):
        self.client.start()
        self.client.wait_for_startup()
        self.setDriver("ST", 1)

    def stop(self):
        self.client.stop()

    def set_power(self, val):
        self.l_debug("set_power", "CMD Power: {}".format("True" if val else "False"))
        self.client.set_power(val == 1)

    def set_mute(self, val):
        self.l_debug("set_mute", "CMD Mute: {}".format("True" if val else "False"))
        self.client.set_mute(val == 1)

    def set_volume(self, val):
        self.l_debug("set_volume", "CMD Volume: {}".format(val))
        self.client.set_volume_db(float(val))

    def set_source(self, val):
        self.l_debug("set_volume", "CMD Source: {}".format(VSX1021Client.INVERTED_INPUTS[val]))
        self.client.set_source(val)

    def on_power(self, power_state):
        self.l_debug("on_power", "{}".format("True" if power_state else "False"))
        self.setDriver("GV2", 1 if power_state else 0)
        if not power_state:
            self.setDriver("GV5", 999)

    def on_volume(self, volume):
        self.l_debug("on_volume", "{}".format(volume))
        self.setDriver("GV4", self.client.volume_db)

    def on_mute(self, mute_state):
        self.l_debug("on_mute", "{}".format("True" if mute_state else "False"))
        self.setDriver("GV3", 1 if mute_state else 0)

    def on_source(self, source):
        self.l_debug("on_source", "{}".format(VSX1021Client.INVERTED_INPUTS[source]))
        self.setDriver("GV5", source)

    """
    Command Functions
    """
    def cmd_set_power(self, command):
        val = command.get("value")
        self.l_info("cmd_set_power", val)
        self.set_power(val == "1")

    def cmd_set_mute(self, command):
        val = command.get("value")
        self.l_info("cmd_set_mute", val)
        self.set_mute(val == "1")

    def cmd_set_volume(self, command):
        val = command.get("value")
        self.l_info("cmd_set_volume", val)
        self.set_volume(val)

    def cmd_set_source(self, command):
        val = command.get("value")
        self.l_info("cmd_set_source", val)
        self.set_source(val)

    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" % (self.id, name, string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.id, name, string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id, name, string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id, name, string))

    my_commands = {
        "SET_POWER": cmd_set_power,
        "SET_MUTE": cmd_set_mute,
        "SET_VOLUME": cmd_set_volume,
        "SET_SOURCE": cmd_set_source
    }
