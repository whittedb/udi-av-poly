"""
This is a NodeServer for the Pioneer VSX-1021 A/V Receiver for Polyglot v2 written in Python3
by Brad Whitted brad_whitted@gmail.com
"""
import polyinterface

LOGGER = polyinterface.LOGGER


class AVNode(polyinterface.Node):
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

        self.id = self.TYPE
        super().__init__(controller, primary, address, name)

    def set_power(self, on_off):
        pass

    def set_mute(self, on_off):
        pass

    def set_volume(self, volume):
        pass

    def set_input(self, source):
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
        {"driver": "SVOL", "value": -80, "uom": 56},  # Volume
        {"driver": "GV4", "value": 999, "uom": 25}  # Input Source
    ]
