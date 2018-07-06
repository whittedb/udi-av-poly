import logging
from threading import Event, RLock
from transitions.extensions import LockedMachine as Machine


class StateMachine(Machine):
    def __init__(self):
        states = [
            "not_running",
            "starting",
            "connecting",
            "connected",
            "running",
            "disconnecting",
            "shutting_down",
            "connect_error",
            "socket_error",
            "error"
        ]
        transitions = [
            {"trigger": "start", "source": "not_running", "dest": "starting"},
            {"trigger": "connect_to_device", "source": "starting", "dest": "connecting"},
            {"trigger": "connected_to_device", "source": "connecting", "dest": "connected"},
            {"trigger": "enter_run", "source": "connected", "dest": "running"},

            {"trigger": "close", "source": "running", "dest": "disconnecting"},
            {"trigger": "close", "source": "not_running", "dest": "="},
            {"trigger": "disconnected", "source": "disconnecting", "dest": "not_running"},
            {"trigger": "shutdown", "source": "*", "dest": "shutting_down"},

            {"trigger": "connection_error", "source": "connecting", "dest": "error"},
            {"trigger": "read_error", "source": "running", "dest": "error"},

        ]
        super().__init__(model=None, states=states, transitions=transitions,
                         initial="not_running", send_event=True, queued=True, auto_transitions=False)


class AvReceiver(object):
    """
    Trigger methods created by the state machine

    start(): Connects to device and starts reading from it
    close(): Stops reading from device and disconnects from it
    shutdown(): Disconnects from device and enters a shutdown state.  There is no way to restart from here.
    """
    _stateMachine = StateMachine()

    def __init__(self, name, logger):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
        self._shutdownEvent = Event()
        self._startupComplete = Event()
        self._stateMachineLock = RLock()
        self._name = name
        self._power = None
        self._volume = None
        self._mute = None
        self._source = None

        self._stateMachine.add_model(model=self, model_context=self._stateMachineLock)

    def run(self):
        """
        Easy way to initiate a start and wait for a shutdown (Useful as a Thread target)
        :return:
        """
        self.start()
        self._shutdownEvent.wait()

    def wait_for_startup(self):
        self._startupComplete.wait()

    def wait_for_shutdown(self):
        self._shutdownEvent.wait()

    def stop(self):
        """
        Easy method to execute a shutdown and wait for the shutdown to complete
        :return:
        """
        self.shutdown()
        self.wait_for_shutdown()

    # State machine handlers
    def on_enter_not_running(self, event):
        self.logger.info("A/V device not running: " + self._name)
        self._startupComplete.set()

    def on_enter_starting(self, event):
        self.logger.info("Starting A/V device: " + self._name)
        self._startupComplete.clear()
        self.connect_to_device()

    def on_enter_connecting(self, event):
        self.logger.info("Connecting to A/V device: " + self._name)

        rv = self.connect()
        if rv:
            self.connected_to_device()
        else:
            self.connect_error(event)

    def on_enter_connected(self, event):
        self.logger.info("Connected to A/V device: " + self._name)
        self.start_receiver_thread()
        self.enter_run()

    def on_enter_running(self, event):
        self.logger.info("A/V Device Active: " + self._name)
        self.initialize_state()
        self._startupComplete.set()

    def on_enter_disconnecting(self, event):
        self.logger.info("Disconnecting from A/V device: " + self._name)
        self.stop_receiver_thread()
        self.disconnect()
        self.disconnected()

    def on_enter_shutting_down(self, event):
        self.logger.info("Shutting down A/V device: " + self._name)
        self.stop_receiver_thread()
        self.disconnect()
        self._shutdownEvent.set()

    def on_enter_error(self, event):
        self.logger.error("A/V device error: {} - {}".format(self._name, event))

    """
    These methods are called by the state machine.
    Override them as needed.  No super is required in the overridden methods
    """
    def connect(self):
        return True

    def disconnect(self):
        pass

    def start_receiver_thread(self):
        pass

    def stop_receiver_thread(self):
        pass

    def initialize_state(self):
        pass

    # Override these in sub classes for specific behavior
    @property
    def power(self):
        return self._power

    # Get raw device volume
    @property
    def volume(self):
        return self._volume

    @property
    def mute(self):
        return self._mute

    # Get raw device input source value
    @property
    def source(self):
        "Get current source input selection"""
        return self._source

    def set_power(self, power_state):
        self._power = power_state

    # Set raw device volume
    def set_volume(self, volume):
        self._volume = volume

    def set_mute(self, mute_state):
        self._mute = mute_state

    # Set raw device input source value
    def set_source(self, source):
        self._source = source
