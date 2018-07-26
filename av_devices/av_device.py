import logging
from threading import Event, RLock
from transitions.extensions.states import add_state_features, Timeout
from transitions.extensions import LockedMachine as Machine


@add_state_features(Timeout)
class StateMachine(Machine):
    def __init__(self):
        states = [
            "not_running",
            "starting",
            "running",
            "disconnecting",
            "shutting_down",
            "error",
            {"name": "reconnecting", "timeout": 10, "on_timeout": "start"}
        ]
        transitions = [
            {"trigger": "start", "source": ["not_running", "reconnecting"], "dest": "starting"},
            {"trigger": "started", "source": "starting", "dest": "running"},
            {"trigger": "disconnected", "source": "disconnecting", "dest": "not_running"},
            {"trigger": "close", "source": "running", "dest": "disconnecting"},
            {"trigger": "close", "source": "not_running", "dest": "="},
            {"trigger": "shutdown", "source": "*", "dest": "shutting_down"},
            {"trigger": "reconnect", "source": "error", "dest": "reconnecting"},

            {"trigger": "handle_error", "source": ["starting", "running"], "dest": "error"},
        ]
        super().__init__(model=None, states=states, transitions=transitions,
                         initial="not_running", send_event=True, queued=True, auto_transitions=False)


class AvDevice(object):
    """
    Trigger methods created by the state machine

    start(): Connects to device and starts reading from it
    close(): Stops reading from device and disconnects from it
    shutdown(): Disconnects from device and enters a shutdown state.  There is no way to restart from here.
    """
    _stateMachine = StateMachine()

    class Listener(object):
        def on_power(self, power_state):
            pass

        def on_volume(self, volume):
            pass

        def on_mute(self, mute_state):
            pass

        def on_input(self, input_value):
            pass

        def on_connected(self):
            pass

        def on_disconnected(self):
            pass

        def on_responding(self):
            pass

        def on_not_responding(self):
            pass

    class Error(Exception):
        def __init__(self, msg):
            super().__init__(msg)

    class NotResponding(Exception):
        def __init__(self):
            super().__init__("Device not responding")

    def __init__(self, name, logger=None):
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
        self._shutdownEvent = Event()
        self._startupComplete = Event()
        self._stateMachineLock = RLock()
        self._name = name
        self._power = False
        self._volume = 0
        self._mute = False
        self._input = None
        self.listeners = []

        self._stateMachine.add_model(model=self, model_context=self._stateMachineLock)

    def add_listener(self, listener):
        self.listeners.append(listener)

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

        self.logger.info("Connecting to A/V device: " + self._name)
        try:
            try:
                self.connect()
            except Exception as e:
                self.handle_error(error=e)
                return

            self.logger.info("Connected to A/V device: " + self._name)
            self.start_listener_thread()
            self.started()
        except Exception as e:
            self.handle_error(error=e)

    def on_enter_running(self, event):
        self.logger.info("A/V Device Active: " + self._name)
        for l in self.listeners:
            l.on_connected()
        self.initialize_state()
        self._startupComplete.set()

    def on_enter_disconnecting(self, event):
        self.logger.info("Disconnecting from A/V device: " + self._name)
        self.stop_listener_thread()

        try:
            self.disconnect()
        except Exception:
            pass
        for l in self.listeners:
            l.on_disconnected()

        self.disconnected()

    def on_enter_shutting_down(self, event):
        self.logger.info("Shutting down A/V device: " + self._name)
        self.stop_listener_thread()
        try:
            self.disconnect()
        except Exception:
            pass
        for l in self.listeners:
            l.on_disconnected()
        self._shutdownEvent.set()

    def on_enter_reconnecting(self, event):
        self.logger.info("Attempting {} reconnect in {} seconds...".format(self._name, event.state.timeout))

    def on_enter_error(self, event):
        e = event.kwargs.get("error")
        source = event.transition.source

        self.logger.error("{} device error in state: {} - {}".format(self._name, source, e))
        if source == "running":
            if isinstance(e, AvDevice.NotResponding):
                for l in self.listeners:
                    l.on_not_responding()

            self.stop_listener_thread(socket_error=True)
            try:
                self.disconnect()
            except Exception as e:
                self.logger.error("{} unhandled error: {}".format(self._name, e))
                pass

            self.reconnect()
        elif source == "starting":
            for l in self.listeners:
                l.on_not_responding()
            self.reconnect()

    """
    These methods are called by the state machine.
    Override them as needed.  No super is required in the overridden methods
    """
    def connect(self):
        return True

    def disconnect(self):
        pass

    def start_listener_thread(self):
        pass

    def stop_listener_thread(self, socket_error=False):
        pass

    def initialize_state(self):
        pass

    @property
    def name(self):
        return self._name

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
    def input(self):
        return self._input

    @power.setter
    def power(self, power_state):
        self._power = power_state
        for l in self.listeners:
            l.on_power(self.power)

    # Set raw device volume
    @volume.setter
    def volume(self, volume):
        self._volume = volume
        for l in self.listeners:
            l.on_volume(self.volume)

    @mute.setter
    def mute(self, mute_state):
        self._mute = mute_state
        for l in self.listeners:
            l.on_mute(self.mute)

    # Set raw device input value
    @input.setter
    def input(self, input_value):
        self._input = input_value
        for l in self.listeners:
            l.on_input(self.input)
