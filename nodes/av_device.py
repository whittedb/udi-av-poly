"""
This is a NodeServer for the Pioneer VSX-1021 A/V Receiver for Polyglot v2 written in Python3
by Brad Whitted brad_whitted@gmail.com
"""
import polyinterface

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

    def __init__(self, controller, primary, address=None, name=None, uom=None, tdata=None, is_new=True):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """

        LOGGER.debug("AVDevice:__init__: start: address={} name={} type={} uom={}".format(address, name, type, uom))

        self.address = address
        self.id = "avDevice"    # Until we figure out the uom
        self.name = name
        self.is_new = is_new
        self.controller = controller
        self.primary_n = controller.nodes[primary]

        if is_new:
            # It's a new device
            self.address = address
            if tdata is None:
                self.l_error('__init__',
                             "New node address ({0}), name ({1}), and type ({2}) must be specified when tdata is None"
                             .format(address, name, tag_type))
                return
            if uom is None:
                self.l_error('__init__',"uom ({0}) must be specified for new tags.".format(uom))
            self.l_debug('__init__','New node {}'.format(tdata))
            device_type = tdata['deviceType']
            self.tag_uom = uom
            device_id = tdata['slaveId']
            self.uuid = tdata['uuid']
            address = id_to_address(self.uuid)
            name = tdata['name']

        super(AVDevice, self).__init__(controller, primary, address, name)

    def l_info(self, name, string):
        LOGGER.info("%s:%s:%s:%s:%s: %s" % (self.primary_n.name, self.name, self.address, self.id, name, string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s:%s:%s:%s: %s" % (self.primary_n.name, self.name, self.address, self.id, name, string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s:%s:%s:%s: %s" % (self.primary_n.name, self.name, self.address, self.id, name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s:%s:%s: %s" % (self.primary_n.name, self.name, self.address, self.id, name, string))

