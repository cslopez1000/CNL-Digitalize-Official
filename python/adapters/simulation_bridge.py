"""Small adapter between CST's existing queue API and native simulation.

All packets enter the CST beam buffer on a background collector before display
decimation. Command scaling is performed by CST's existing controller. Native
simulation consumes those raw command values and produces raw readbacks.
"""
from queue import Empty, Full, Queue
from threading import Event, Thread, Lock
import time

import CombinationBackend
from source.Python.Control.pid_beam_buffer import BEAM_BUFFER
from source.Python.Data.simulation_recorder import SimulationRecorder
from source.Python.Services.beam_cal import beam_cal
from source.Python.Services.beam_range import RangeCodec
from source.Python.Services.scaling import get_scaler


class SimulationBridge:
    def __init__(self, database_path, rate_hz=100):
        self.native = CombinationBackend.SimulationRuntime(rate_hz)
        self.data_queue = Queue(maxsize=1)
        self._subscriptions = {self.data_queue}
        self._subscription_lock = Lock()
        self.recorder = SimulationRecorder(database_path)
        self.mode = "MANUAL"
        self.range_index = int(beam_cal.cfg.manual_index)
        self.bitmask = RangeCodec.compose(0, self.range_index)
        self.direct_beam = False
        self.error = ""
        self.received_packets = 0
        self.last_packet = None
        self._stop = Event()
        self._collector = None
        # Do not assume Python and C++ steady clocks share an epoch on every OS.
        self._clock_offset = time.monotonic() - CombinationBackend.monotonic_seconds()

    def subscribe(self):
        """Give each window its own bounded latest-packet mailbox.

        Acquisition, PID buffering and persistence remain full rate. Slow or
        hidden views may skip display frames without blocking other consumers.
        """
        mailbox = Queue(maxsize=1)
        with self._subscription_lock:
            self._subscriptions.add(mailbox)
            if self.last_packet is not None:
                mailbox.put_nowait(self.last_packet)
        return mailbox

    def unsubscribe(self, mailbox):
        with self._subscription_lock:
            self._subscriptions.discard(mailbox)

    def _publish(self, packet):
        with self._subscription_lock:
            self.last_packet = packet
            for mailbox in self._subscriptions:
                try:
                    mailbox.get_nowait()
                except Empty:
                    pass
                try:
                    mailbox.put_nowait(packet)
                except Full:
                    pass

    def configure_calibration(self):
        """Use CST's exact selected LUT/gain; simulate its inverse, not RI defaults."""
        calibration = beam_cal.cfg.ranges[self.range_index]
        inverse = [(float(current), float(voltage)) for voltage, current in calibration.curve] if calibration.mode == "curve" else []
        self.native.configure_beam(self.range_index, self.bitmask, inverse, calibration.gain_na_per_v,
                                   calibration.offset_na, self.direct_beam)
        scaler = get_scaler()
        scaler.reload_if_changed()
        entry = scaler.data.get("ch10", {})
        mapping = entry.get("raw_to_eng", {}) if entry.get("enabled", True) else {}
        points = mapping.get("points", []) if mapping.get("type") == "curve" else []
        # CST scaling deduplicates by X, retaining the last configured value.
        curve = list({float(x): float(y) for x, y in points}.items())
        self.native.configure_actuator(curve, float(mapping.get("gain", 1)), float(mapping.get("offset", 0)))

    def start(self):
        if self._collector is not None:
            return
        BEAM_BUFFER.clear()
        self.configure_calibration()
        self.native.start()
        self._collector = Thread(target=self._collect, name="native-simulation-collector", daemon=True)
        self._collector.start()

    def set_mode(self, mode):
        self.native.set_mode(str(mode))
        self.mode = str(mode)

    def put(self, payload, block=True, timeout=None):
        """CST queue-compatible command sink. No network or hardware API exists."""
        if isinstance(payload, dict):
            if payload.get("cmd") != "set_beam_range":
                raise ValueError("Unsupported simulation command")
            index = payload["beam_range_idx"]
            if int(index) != index or not 0 <= int(index) < len(beam_cal.cfg.ranges):
                raise ValueError("Invalid beam range")
            previous = self.range_index, self.bitmask
            self.range_index = int(index)
            self.bitmask = int(payload["bitmask_u64"])
            try:
                self.configure_calibration()
            except Exception:
                self.range_index, self.bitmask = previous
                raise
            return
        targets, power, enabled = payload
        self.native.send(list(targets), list(power), list(enabled), self.mode)

    def _drain(self):
        packets = self.native.drain()
        for packet in packets:
            packet["_pid_rx_mono"] = packet.pop("_native_rx_mono") + self._clock_offset
            if packet["simulation_direct_beam"] == self.direct_beam:
                BEAM_BUFFER.add_packet(packet)
        if packets:
            self.received_packets += len(packets)
            if not self.recorder.record(packets):
                self.error = "Database recording queue is full"
            visible = [packet for packet in packets if packet["simulation_direct_beam"] == self.direct_beam]
            if not visible:
                return
            self._publish(visible[-1])

    def _collect(self):
        try:
            while not self._stop.wait(0.01):
                self._drain()
        except Exception as exc:
            self.error = str(exc)

    def close(self):
        self.native.stop()
        self._stop.set()
        if self._collector is not None:
            self._collector.join(timeout=3)
            if self._collector.is_alive():
                raise RuntimeError("Simulation collector did not stop")
        self._drain()
        self.recorder.close()
        if self.error:
            raise RuntimeError(f"Simulation acquisition/recording error: {self.error}")
