import polyinterface
import logging
import asyncore
import struct
from queue import PriorityQueue, Queue
import time
from enum import unique, Enum
from threading import Thread, Event, Lock
from av_devices.av_device import AvDevice


LOGGER = polyinterface.LOGGER


@unique
class Type(Enum):
    CONTROL = "C"
    ENQUIRY = "E"
    ANSWER = "A"
    NOTIFY = "N"


@unique
class Answer(Enum):
    # Fill out to 16 characters
    SUCCESS = "0" * 16
    ERROR = "F" * 16
    NOT_FOUND = "N" * 16


@unique
class Functions(Enum):
    IRCC_CODE = "IRCC"
    POWER_STATUS = "POWR"
    VOLUME = "VOLU"
    MUTE = "AMUT"
    SET_CHANNEL = "CHNN"
    TRIPLET_CHANNEL = "TCHN"
    INPUT_SOURCE = "ISRC"
    INPUT = "INPT"
    PICTURE_MUTE = "PMUT"
    TOGGLE_PICTURE_MUTE = "TPMU"
    PIP = "PIPI"
    TOGGLE_PIP = "TPIP"
    TOGGLE_PIP_POSITION = "TPPP"


@unique
class IrccCommands(Enum):
    POWER_OFF = 0
    INPUT = 1
    GGUIDE = 2
    EPG = 3
    FAVORITES = 4
    DISPLAY = 5
    HOME = 6
    OPTIONS = 7
    RETURN = 8
    UP = 9
    DOWN = 10
    RIGHT = 11
    LEFT = 12
    CONFIRM = 13
    RED = 14
    GREEN = 15
    YELLOW = 16
    BLUE = 17
    NUM1 = 18
    NUM2 = 19
    NUM3 = 20
    NUM4 = 21
    NUM5 = 22
    NUM6 = 23
    NUM7 = 24
    NUM8 = 25
    NUM9 = 26
    NUM0 = 27
    NUM11 = 28
    NUM12 = 29
    VOLUME_UP = 30
    VOLUME_DOWN = 31
    MUTE = 32
    CHANNEL_UP = 33
    CHANNEL_DOWN = 34
    SUBTITLE = 35
    CLOSED_CAPTION = 36
    ENTER = 37
    DOT = 38
    ANALOG = 39
    TELETEXT = 40
    EXIT = 41
    ANALOG2 = 42
    AD = 43
    DIGITAL = 44
    ANALOG_ = 45
    BS = 46
    CS = 47
    BS_CS = 48
    DDATA = 49
    PIC_OFF = 50
    TV_RADIO = 51
    THEATER = 52
    SEN = 53
    INTERNET_WIDGETS = 54
    INTERNET_VIDEO = 55
    NETFLIX = 56
    SCENE_SELECT = 57
    MODE3D = 58
    IMANUAL = 59
    AUDIO = 60
    WIDE = 61
    JUMP = 62
    PAP = 63
    MYEPG = 64
    PROGRAM_DESCRIPTION = 65
    WRITE_CHAPTER = 66
    TRACK_ID = 67
    TEN_KEY = 68
    APPLICAST = 69
    AC_TVILA = 70
    DELETE_VIDEO = 71
    PHOTO_FRAME = 72
    TV_PAUSE = 73
    KEYPAD = 74
    MEDIA = 75
    SYNC_MENU = 76
    FORWARD = 77
    PLAY = 78
    REWIND = 79
    PREV = 80
    STOP = 81
    NEXT = 82
    REC = 83
    PAUSE = 84
    EJECT = 85
    FLASH_PLUS = 86
    FLASH_MINUS = 87
    TOP_MENU = 88
    POPUP_MENU = 89
    RAKURAKU_START = 90
    ONE_TOUCH_TIME_RECORD = 91
    ONE_TOUCH_VIEW = 92
    ONE_TOUCH_RECORD = 93
    ONE_TOUCH_STOP = 94
    DUX = 95
    FOOTBALL_MODE = 96
    SOCIAL = 97

    def __new__(cls, v):
        obj = object.__new__(cls)
        # Zero pad
        obj._value_ = str(v).zfill(16)
        return obj


@unique
class Inputs(Enum):
    TV = 0, (0, 0)
    HDMI1 = 1, (1, 1)
    HDMI2 = 2, (1, 2)
    HDMI3 = 3, (1, 3)
    HDMI4 = 4, (1, 4)
    COMPOSITE = 5, (3, 1)
    COMPONENT = 6, (4, 1)
    SCREEN_MIRROR = 7, (5, 1)
    UNKNOWN = 999, (-1, -1)

    def __new__(cls, keycode, param):
        obj = object.__new__(cls)
        # Build parameter to send to device
        obj._value_ = keycode
        obj.code = str(param[0]).zfill(8) + str(param[1]).zfill(8)
        return obj

    @classmethod
    def get_by_code(cls, code):
        for name, member in cls.__members__.items():
            if member.code == code:
                return member
        else:
            return cls.UNKNOWN


class CommData(object):
    MSGLEN = 24
    _commData = struct.Struct("2sc4s16sc")
    _header = b"*S"
    _footer = bytes([0x0a])

    def __init__(self, ctype=Type.CONTROL, function="", parameter=""):
        self._lock = Lock()
        with self._lock:
            self.ctype = ctype.value
            if function == "":
                self.function = "#" * 16
            else:
                self.function = function
            if parameter == "":
                self.parameter = "#" * 16
            else:
                self.parameter = parameter

    def set_power(self, on_off=False):
        with self._lock:
            self.function = Functions.POWER_STATUS.value
            self.parameter = ("1" if on_off else "0").zfill(16)
            return self

    def get_power(self):
        with self._lock:
            self.ctype = Type.ENQUIRY.value
            self.function = Functions.POWER_STATUS.value
            return self

    def set_mute(self, on_off):
        with self._lock:
            self.function = Functions.MUTE.value
            self.parameter = ("1" if on_off else "0").zfill(16)
            return self

    def get_mute(self):
        with self._lock:
            self.ctype = Type.ENQUIRY.value
            self.function = Functions.MUTE.value
            return self

    def set_volume(self, volume):
        with self._lock:
            self.function = Functions.VOLUME.value
            self.parameter = volume.zfill(16)
            return self

    def get_volume(self):
        with self._lock:
            self.ctype = Type.ENQUIRY.value
            self.function = Functions.VOLUME.value
            return self

    def volume_up(self):
        with self._lock:
            self.function = Functions.IRCC_CODE.value
            self.parameter = IrccCommands.VOLUME_UP.value
            return self

    def volume_down(self):
        with self._lock:
            self.function = Functions.IRCC_CODE.value
            self.parameter = IrccCommands.VOLUME_DOWN.value
            return self

    def set_input(self, input_value):
        with self._lock:
            self.function = Functions.INPUT.value
            self.parameter = Inputs[input_value].code
            return self

    def get_input(self):
        with self._lock:
            self.ctype = Type.ENQUIRY.value
            self.function = Functions.INPUT.value
            return self

    def goto_netflix(self):
        with self._lock:
            self.function = Functions.IRCC_CODE.value
            self.parameter = IrccCommands.NETFLIX.value
            return self

    def pack(self):
        with self._lock:
            return self._commData.pack(
                    self._header, self.ctype.encode(), self.function.encode(), self.parameter.encode(), self._footer)

    def unpack(self, data):
        with self._lock:
            self._header, self.ctype, self.function, self.parameter, self._footer = self._commData.unpack(data)
            self.ctype = self.ctype.decode()
            self.function = self.function.decode()
            self.parameter = self.parameter.decode()
            return self


class ClientHandler(asyncore.dispatcher):
    DEAD_THREAD = Thread()

    class Listener(object):
        def on_connection_handler_response(self, data):
            pass

        def on_connection_closed(self):
            pass

        def on_connection_error(self, error):
            pass

    def __init__(self, host, port, logger, listener=None):
        self.logger = logger
        self._host = host
        self._port = port
        self._connectionHandlerThread = self.DEAD_THREAD
        self._stopThread = Event()
        self._sendQ = PriorityQueue()
        self._waitForResponseQ = Queue()
        self._writeBuffer = []
        self._listeners = []
        if listener is not None:
            self._listeners.append(listener)
        super().__init__()

    def add_listener(self, listener):
        self._listeners.append(listener)

    def handle_connect(self):
        self.logger.info("Sony Bravia TV: Connected")

    def handle_close(self):
        self.close()
        self.logger.info("Sony Bravia TV: Disconnected")

    def writable(self):
        return (len(self._writeBuffer) > 0 or not self._sendQ.empty()) and self._waitForResponseQ.empty()

    def readable(self):
        return True

    def handle_read(self):
        received = self.recv(CommData.MSGLEN)
        if received == b"":
            for l in self._listeners:
                l.on_connection_closed()
            return

        self.logger.debug("<-- Raw: {}".format(received))
        data = CommData().unpack(received)
        if data.ctype == Type.ANSWER.value:
            if not self._waitForResponseQ.empty():
                self._waitForResponseQ.get()
                self._waitForResponseQ.task_done()

        for l in self._listeners:
            l.on_connection_handler_response(data)

    def handle_write(self):
        if len(self._writeBuffer) > 0:
            data = self._writeBuffer.pop()
        else:
            _, data = self._sendQ.get()
            self._sendQ.task_done()
            # Need to stash this so we can check for a response in the reader
            self._waitForResponseQ.put(data)
            data = data.pack()
            self.logger.debug("--> Raw: {}".format(data))

        sent = self.send(data)
        if sent < len(data):
            remaining = data[sent:]
            self._writeBuffer.append(remaining)

    def start(self):
        try:
            self.create_socket()
            self.connect((self._host, self._port))

            if self._connectionHandlerThread is self.DEAD_THREAD:
                self.logger.debug("Sony Bravia TV: Starting connection handler")
                self._connectionHandlerThread = Thread(
                        name="Sony Bravia TV Connection Handler", target=self._connection_handler)
                self._stopThread.clear()
                self._connectionHandlerThread.start()
        except Exception as e:
            self.logger.exception("Sony Bravia: Connection handler error while connecting: {}".format(e))
            raise

    def stop(self):
        if self._connectionHandlerThread is not self.DEAD_THREAD:
            self.logger.debug("Sony Bravia TV: Stopping connection handler")
            with self._stopThread:
                self._stopThread.set()
            self._connectionHandlerThread.join()
            self._connectionHandlerThread = self.DEAD_THREAD
            self.handle_close()

    def send_command(self, data):
        self.logger.debug("Queueing Request: {}".format(data.pack()))
        self._sendQ.put((time.time(), data))

    def _connection_handler(self):
        self.logger.debug("Sony Bravia: Starting connection handler thread")
        while True:
            asyncore.loop(3)
            if self._stopThread.is_set():
                break

        self.logger.debug("Sony Bravia: Exiting connection handler thread")


class SonyBraviaXBR65X810CDevice(AvDevice, ClientHandler.Listener):
    INPUTS = {name: member.value for name, member in Inputs.__members__.items()}
    INVERTED_INPUTS = {member.value: name for name, member in Inputs.__members__.items()}
    DEAD_THREAD = Thread()

    def __init__(self, name, ip, port=20060, logger=None):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
        super().__init__(name, logger)
        self._ip = ip
        self._port = port
        self._connectionHandler = ClientHandler(self._ip, int(self._port), self.logger, self)

    def connect(self):
        if self._connectionHandler is None:
            self._connectionHandler = ClientHandler(self._ip, int(self._port), self.logger, self)
        self._connectionHandler.start()

    def disconnect(self):
        if self._connectionHandler is not None:
            self._connectionHandler.stop()
            self._connectionHandler = None

    def initialize_state(self):
        self.query_device()
        time.sleep(1)

    "Turn device on/off"""
    def set_power(self, turn_on):
        self._send(CommData().set_power(turn_on))

    "Mute/Unmute sound"""
    def set_mute(self, mute_on):
        self._send(CommData().set_mute(mute_on))

    "Set volume to specific value on 0-100 scale"""
    def set_volume(self, volume):
        self._send(CommData().set_volume(volume))

    "Send request to increment volume by 1 unit"""
    def volume_up(self):
        self._send(CommData().volume_up())

    "Send request to decrease volume by 1 unit"""
    def volume_down(self):
        self._send(CommData().volume_down())

    "Send request to change input selector"""
    def set_input(self, input_value):
        self._send(CommData().set_input(input_value))

    def query_power(self):
        self._send(CommData(Type.ENQUIRY).get_power())

    def query_volume(self):
        self._send(CommData(Type.ENQUIRY).get_volume())

    def query_input(self):
        self._send(CommData(Type.ENQUIRY).get_input())

    def query_mute(self):
        self._send(CommData(Type.ENQUIRY).get_mute())

    def query_device(self):
        self.query_power()
        self.query_volume()
        self.query_mute()
        self.query_input()

    def on_connection_handler_response(self, data):
        self._update_states(data)

    def on_connection_closed(self):
        self.handle_error(error=AvDevice.Error("Sony Bravia: Connection closed"))

    def on_connection_error(self, error):
        self.handle_error(error=AvDevice.Error("Sony Bravia: Connection error"))

    def _update_states(self, comm):
        for l in self.listeners:
            l.on_responding()

        if comm.ctype != Type.ANSWER.value and comm.ctype != Type.NOTIFY.value:
            self.logger.error("Sony Bravia response not an Answer or Notify type")
            return

        if comm.parameter == Answer.ERROR.value:
            self.logger.error("Sony Bravia response error recieved")
            return

        if comm.parameter == Answer.NOT_FOUND.value:
            self.logger.error("Sony Bravia response: Not Found")
            return

        # Ignore success responses.  We'll get a notification with the change
        if comm.parameter == Answer.SUCCESS.value:
            return

        command = comm.function
        if command == Functions.POWER_STATUS.value:
            super().set_power(int(comm.parameter) == 1)
        elif command == Functions.MUTE.value:
            super().set_mute(int(comm.parameter) == 1)
        elif command == Functions.VOLUME.value:
            super().set_volume(int(comm.parameter))
        elif command == Functions.INPUT.value:
            v = Inputs.get_by_code(comm.parameter)
            if v is Inputs.UNKNOWN:
                self.logger.debug("Sony Bravia returned unknown source value")
            else:
                super().set_source(v.value)

    "Sends single command to AV"""
    def _send(self, data):
        if not self.is_running() or self._connectionHandler is None:
            return

        data_len = len(data.pack())
        if data_len != CommData.MSGLEN:
            self.logger.debug("Message data length({}) != to required {}".format(data_len, CommData.MSGLEN))
            return

        self._connectionHandler.send_command(data)
