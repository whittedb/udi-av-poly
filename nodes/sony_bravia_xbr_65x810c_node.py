import polyinterface
from .av_node import AVNode
from av_devices.av_device import AvDevice
from av_devices import SonyBraviaXBR65X810CDevice


LOGGER = polyinterface.LOGGER


class SonyBraviaXBR65X810CNode(AVNode, AvDevice.Listener):
    TYPE = "BRAVIA"

    def __init__(self, controller, primary, host, port, address=None, name=None):
        self.host = host
        self.port = port
        self.commands.update(self.bravia_commands)
        self.drivers.extend(self.bravia_drivers)
        super().__init__(controller, primary, address, name)
        self.client = SonyBraviaXBR65X810CDevice(self.TYPE + ":" + name, self.host, self.port, logger=LOGGER)
        self.client.add_listener(self)

    def start(self):
        self.client.start()
        self.client.wait_for_startup()
        self.setDriver("GV1", 2)
        self.reportDrivers()

    def stop(self):
        self.client.stop()
        self.reportDrivers()

    def set_power(self, val):
        self.l_debug("set_power", "CMD Power: {}".format("True" if val else "False"))
        self.client.set_power(val == 1)

    def on_responding(self):
        self.setDriver("ST", 1)
        # self.reportDrivers()

    def on_not_responding(self):
        self.setDriver("ST", 0)
        # self.reportDrivers()

    def set_mute(self, val):
        self.l_debug("set_mute", "CMD Mute: {}".format("True" if val else "False"))
        self.client.set_mute(val == 1)

    def set_volume(self, val):
        self.l_debug("set_volume", "CMD Volume: {}".format(val))
        self.client.set_volume(val)

    def set_source(self, val):
        try:
            self.l_debug("set_source", "CMD Source: {}".format(
                    SonyBraviaXBR65X810CDevice.INVERTED_INPUTS[str(val).zfill(2)]))
        except KeyError:
            pass
        self.client.set_source(val)

    def on_connected(self):
        self.setDriver("ST", 1)

    def on_disconnected(self):
        self.setDriver("ST", 0)

    def on_power(self, power_state):
        self.l_debug("on_power", "{}".format("True" if power_state else "False"))
        self.setDriver("GV2", 1 if power_state else 0)
        if not power_state:
            self.setDriver("GV5", 999)

    def on_volume(self, volume):
        self.l_debug("on_volume", "{}".format(volume))
        self.setDriver("GV4", self.client.volume)

    def on_mute(self, mute_state):
        self.l_debug("on_mute", "{}".format("True" if mute_state else "False"))
        self.setDriver("GV3", 1 if mute_state else 0)

    def on_source(self, source):
        source = int(source)
        try:
            self.l_debug("on_source", "{}".format(SonyBraviaXBR65X810CDevice.INVERTED_INPUTS[source]))
        except KeyError:
            pass
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

    bravia_commands = {
        "SET_POWER": cmd_set_power,
        "SET_MUTE": cmd_set_mute,
        "SET_VOLUME": cmd_set_volume,
        "SET_SOURCE": cmd_set_source
    }

    bravia_drivers = [
    ]
