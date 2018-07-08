import logging
import telnetlib
import socket
from threading import Thread
from time import sleep
from av_receivers.av_receiver import AvReceiver


logger = logging.getLogger()


def myround(x, prec=1, base=.5):
    return round(base * round(float(x) / base), prec)


class VSX1021Client(AvReceiver):
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
        self._receiverThread = None
        self._stopReceiver = False
        self._volDbScale = None
        self._vol100Scale = None
        self._sourceText = None

    def connect(self):
        try:
            self._tn = telnetlib.Telnet(self._ip, self._port)
            return True
        except socket.timeout:
            self.logger.error("Error connecting to device")
            return False

    def disconnect(self):
        self._tn.close()

    def start_receiver_thread(self):
        self._receiverThread = Thread(name="VSX1021 Receiver", target=self._receiver_start)
        self._receiverThread.start()

    def stop_receiver_thread(self):
        self.logger.info("Stopping receiver thread")
        self._stopReceiver = True
        # Request some data to speed up the receiver thread shutdown
        self.update_power_state()
        self._receiverThread.join()
        self._receiverThread = None
    
    def initialize_state(self):
        self.update_power_state()
        self.update_volume()
        self.update_mute()
        self.update_source()
        sleep(1)

    "Sends single command to AV"""
    def _send(self, cmd):
        command = cmd + '\r'

        self._tn.read_eager()  # Cleanup any pending output.
        self.logger.debug("--> {}".format(command))
        self._tn.write(command.encode("ascii"))

    "Receive data"""
    def _receive(self):
        data = self._tn.read_eager().replace(b"\r\n", b"").decode("utf-8")
        self.logger.debug("<-- {}".format(data))
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
    def _receiver_start(self):
        self.logger.info("Starting receiver thread")

        self._stopReceiver = False
        while not self._stopReceiver:
            try:
                data_bytes = self._tn.read_until(b"\r\n", 5)
                if data_bytes == b"" or self._stopReceiver:
                    continue

                data = data_bytes.replace(b"\r\n", b"").decode("utf-8")
                self.logger.debug("<-- {}".format(data))

                self.update_state(data)
            except socket.error as e:
                self.logger.debug("Socket error on read, {}".format(e))
                self.read_error(e)

    def query_source(self):
        self._send("FN")

    "Update Power State"""
    def update_state(self, data):
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
            self.logger.warn("COMMAND ERROR")
        if command == "E06":
            self.logger.warn("PARAMETER ERROR")
        if command == "B00":
            self.logger.warn("RECEIVER BUSY")

        command = data[0:2]
        if command == "FN":
            code = data[2:4]
            try:
                self._sourceText = self.INVERTED_INPUTS[code]
            except KeyError:
                self._sourceText = "Unknown input found: {}".format(code)
            super().set_source(code)

    def update_power_state(self):
        self._send("?P")

    def update_volume(self):
        self._send("?V")

    def update_input(self):
        self._send("?F")

    def update_mute(self):
        self._send("?M")

    def update_source(self):
        self._send("?F")

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
        self.logger.debug("Volume: {}, Scaled: {}, Formatted: {}".format(volume, scaled_volume, formatted))
        self._send(formatted)

    "Set volume to specific value on 0-100 scale"""
    def set_volume100(self, volume):
        scaled_volume = int(myround(volume * 1.85, 0, 1))
        formatted = "{}VL".format(str(scaled_volume).zfill(3))
        self.logger.debug("Volume: {}, Scaled: {}, Formatted: {}".format(volume, scaled_volume, formatted))
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
