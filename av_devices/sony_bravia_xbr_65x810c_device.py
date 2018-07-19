import logging
from threading import Thread, Event, Timer
from time import sleep
from av_devices.av_device import AvDevice


logger = logging.getLogger()


class SonyBraviaXBR65X810CDevice(AvDevice):
    def __init__(self, name, ip, port=20060, logger=None):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
        super().__init__(name, logger)
        self._ip = ip
        self._port = port
        self._tn = None
        self._listenerThread = None
        self._stopListener = False
        self._isAliveTimer = None
        self._isAliveAck = Event()
        self._sourceText = None
