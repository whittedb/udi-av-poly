import polyinterface
from .vsx1021_node import VSX1021Node

LOGGER = polyinterface.LOGGER


def build(controller, primary, address=None, device_type=None, host=None, port=None, name=None):
    """
    Build new node.

    :param controller:
    :param primary:
    :param address:
    :param device_type: Device node to build unless "node" parameter is specified
    :param node: If specified, will build from this node data
    :param host:
    :param port:
    :param name:
    :return: new PolyGlot node
    """
    if device_type is None:
        LOGGER.error("device_type not specified for new node")
        return None

    if device_type == VSX1021Node.TYPE:
        return VSX1021Node(controller=controller, primary=primary, address=address,
                           host=host, port=port, name=name)

    return None
