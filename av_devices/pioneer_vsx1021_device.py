import logging
import telnetlib
import socket
from threading import Thread, Event, Timer
from time import sleep
from av_devices.av_device import AvDevice


def myround(x, prec=1, base=.5):
    return round(base * round(float(x) / base), prec)


class PioneerVSX1021Device(AvDevice):
    """ Telnet client to Pioneer VSX 1021 AVR """
    INPUTS = {
        "PHONO":        "00",
        "CD":           "01",
        "TUNER":        "02",
        "CD-R/TAPE":    "03",
        "DVD":          "04",
        "TV/SAT":       "05",
        "VIDEO1":       "10",
        "MULTI CH IN":  "12",
        "VIDEO2":       "14",
        "DVR/BDR":      "15",
        "IPOD/USB":     "17",
        "XM RADIO":     "18",
        "HDMI1":        "19",
        "HDMI2":        "20",
        "HDMI3":        "21",
        "HDMI4":        "22",
        "HDMI5":        "23",
        "BD":           "25",
        "HOME MEDIA GALLERY": "26",
        "SIRIUS":       "27",
        "HDMI CYCLE":   "31",
        "ADAPTER":      "33"
    }

    INVERTED_INPUTS = {v: k for k, v in INPUTS.items()}

    def __init__(self, name, ip, port=23, logger=None):
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
        self._volDbScale = None
        self._vol100Scale = None
        self._sourceText = None

    def connect(self):
        self._tn = telnetlib.Telnet(self._ip, self._port, 10)

    def disconnect(self):
        if self._tn is not None:
            self._tn.close()

    def start_listener_thread(self):
        self._listenerThread = Thread(name="Pioneer VSX1021 Receiver", target=self._input_listener)
        self._listenerThread.start()

    def stop_listener_thread(self, socket_error=False):
        self.logger.debug("VSX1021: Stopping listener thread")
        if self._listenerThread is not None:
            self._cancel_heartbeat()
            self._stopListener = True

            # If we are not stopping due to a connection error, then request some data to speed up the receiver
            # thread shutdown
            if not socket_error:
                self._send("?P")
            self._listenerThread.join()
            self._listenerThread = None
    
    def initialize_state(self):
        self.update_all_states()
        sleep(1)

    "Sends single command to AV"""
    def _send(self, cmd):
        command = cmd + '\r'

        self._tn.read_eager()  # Cleanup any pending output.
        self.logger.debug("VSX1021: --> {}".format(command))
        try:
            self._tn.write(command.encode("ascii"))
        except OSError as e:
            self.handle_error(error=e)

    "Receive data"""
    def _receive(self):
        data = self._tn.read_eager().replace(b"\r\n", b"").decode("utf-8")
        self.logger.debug("VSX1021: <-- {}".format(data))
        return data

    "Send a command and receive the response"""
    def _send_rcv(self, cmd):
        self._send(cmd)
        sleep(0.1)  # Cool-down time (taken from github/PioneerRebel)
        return self._receive()

    "Send CR to wakeup CPU"""
    def _wake_up(self):
        self._send("")
        sleep(1)

    "Continually receive data. Entry point for async read thread."""
    def _input_listener(self):
        self.logger.debug("VSX1021: Starting listener thread")

        self._stopListener = False

        self._start_heartbeat()
        while not self._stopListener:
            try:
                # Short timeout so we don't hang the thread on shutdown
                data_bytes = self._tn.read_until(b"\r\n", 5)
                if data_bytes == b"" or self._stopListener:
                    continue

                self._cancel_heartbeat()
                self._isAliveAck.set()
                data = data_bytes.replace(b"\r\n", b"").decode("utf-8")
                self.logger.debug("VSX1021: <-- {}".format(data))

                self._update_states(data)
                self._start_heartbeat()
            except (socket.error, socket.gaierror, EOFError) as e:
                self.logger.debug("VSX1021: Socket error on read, {}".format(e))
                self._cancel_heartbeat()
                self.handle_error(error=e)

        self._cancel_heartbeat()

        self.logger.debug("VSX1021 listener thread exiting")

    def _check_is_alive(self):
        self._isAliveAck.clear()
        self.update_power()
        if not self._isAliveAck.wait(10):
            self.handle_error(error=AvDevice.NotResponding())
            self._start_heartbeat()

    def _start_heartbeat(self):
        if not self._stopListener:
            self._isAliveTimer = Timer(10, self._check_is_alive)
            self._isAliveTimer.start()

    def _cancel_heartbeat(self):
        if self._isAliveTimer is not None:
            self._isAliveTimer.cancel()
        self._isAliveTimer = None

    def _update_states(self, data):
        for l in self.listeners:
            l.on_responding()

        command = data[0:3]
        value = data[3:]
        if command == "PWR":
            super().set_power(value == "0")
        if command == "VOL":
            vol = int(value)
            self._volDbScale = (vol - 161) / 2
            self._vol100Scale = int(vol / 1.65)
            super().set_volume(vol)
        if command == "MUT":
            super().set_mute(value == "0")
        if command == "E04":
            self.logger.warn("VSX1021: COMMAND ERROR")
        if command == "E06":
            self.logger.warn("VSX1021: PARAMETER ERROR")
        if command == "B00":
            self.logger.warn("VSX1021: RECEIVER BUSY")

        command = data[0:2]
        if command == "FN":
            code = data[2:4]
            try:
                self._sourceText = self.INVERTED_INPUTS[code]
            except KeyError:
                self._sourceText = "Unknown input found: {}".format(code)
            super().set_source(code)

    def update_power(self):
        if self.is_running():
            self._send("?P")

    def update_volume(self):
        if self.is_running():
            self._send("?V")

    def update_input(self):
        if self.is_running():
            self._send("?F")

    def update_mute(self):
        if self.is_running():
            self._send("?M")

    def update_source(self):
        if self.is_running():
            self._send("?F")

    def update_all_states(self):
        if self.is_running():
            self.update_power()
            self.update_volume()
            self.update_mute()
            self.update_input()

    "Returns device volume in -80 - +12 scale (device scale in DB)"""
    @property
    def volume_db(self):
        return self._volDbScale

    @property
    def volume100(self):
        return self._vol100Scale

    "Turn device on/off"""
    def set_power(self, turn_on):
        if turn_on:
            if self.power is None or not self.power:
                "Turn on"""
                self._wake_up()
                self._send("PO")
                sleep(5)  # Wait before allowing any other command.
                self.initialize_state()
        else:
            if self.power is None or self.power:
                "Turn off"""
                self._send("PF")
                sleep(5)  # Wait before allowing any other command.

    "Send request to increment volume by 1 unit"""
    def volume_up(self):
        self._send("VU")

    "Send request to decrease volume by 1 unit"""
    def volume_down(self):
        self._send("VD")

    "Set volume to specific value on -80 - +12 scale (device scale)"""
    def set_volume_db(self, volume):
        scaled_volume = int(round((volume * 2) + 161, 0))
        formatted = "{}VL".format(str(scaled_volume).zfill(3))
        self.logger.debug("VSX1021: Volume: {}, Scaled: {}, Formatted: {}".format(volume, scaled_volume, formatted))
        self._send(formatted)

    "Set volume to specific value on 0-100 scale"""
    def set_volume100(self, volume):
        scaled_volume = int(myround(volume * 1.85, 0, 1))
        formatted = "{}VL".format(str(scaled_volume).zfill(3))
        self.logger.debug("VSX1021: Volume: {}, Scaled: {}, Formatted: {}".format(volume, scaled_volume, formatted))
        self._send(formatted)

    "Mute/Unmute sound"""
    def set_mute(self, mute_on):
        if mute_on:
            self._send("MO")
        else:
            self._send("MF")

    "Send request to change input selector"""
    def set_source(self, value):
        self._send("{}FN".format(str(value).zfill(2)))
