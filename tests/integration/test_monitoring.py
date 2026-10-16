"""Native telemetry broadcast and reused CST transport receive-path checks."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from queue import Empty

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["COMBINATION_RUNTIME_DIR"] = tempfile.mkdtemp(prefix="monitor-tests-", dir=ROOT/"runtime")
from python.application.native_modules import configure_native_path
configure_native_path()
from python.application.paths import configure_environment, runtime_path
configure_environment()
from PySide6.QtWidgets import QApplication
from python.adapters.simulation_bridge import SimulationBridge
from python.application.transport_monitor import SimulationTransportWindow
from python.application.simulation import SimulationControllerWindow
from python.application.magnetic_monitor import SimulationMagneticWindow
from python.app.controls.cst.controller_context import ControlMode
from source.Python.Services.scaling import get_scaler, TRIM_KEYS
from python.application.source_monitor import SimulationSourceWindow
from python.application.simulation_app import SimulationSession


class MonitoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.bridge = SimulationBridge(runtime_path(f"databases/{self._testMethodName}.db"))
        self.bridge.start()
        self.addCleanup(self.bridge.close)

    def wait_packet(self):
        deadline = time.monotonic()+2
        while self.bridge.last_packet is None and time.monotonic()<deadline:
            time.sleep(.01)
        self.assertIsNotNone(self.bridge.last_packet)

    def test_independent_bounded_subscribers_and_late_join(self):
        a, b = self.bridge.subscribe(), self.bridge.subscribe()
        self.wait_packet()
        first = a.get(timeout=1)
        self.assertEqual(len(first["transport"]), 10)
        self.assertTrue(all(v>0 for v in first["transport"]))
        # Draining one view cannot steal the other view's display packet.
        self.assertFalse(b.empty())
        time.sleep(.15)
        self.assertEqual(b.qsize(), 1)
        self.assertGreater(b.get_nowait()["sequence"], first["sequence"])
        late = self.bridge.subscribe()
        self.assertFalse(late.empty())
        self.bridge.unsubscribe(a)
        while not a.empty():
            a.get_nowait()
        time.sleep(.05)
        self.assertTrue(a.empty())
        self.bridge.unsubscribe(b)
        self.bridge.unsubscribe(late)

    def test_cst_readouts_hold_and_shared_backend_survives_window_close(self):
        self.wait_packet()
        controller = SimulationControllerWindow(bridge=self.bridge)
        monitor = SimulationTransportWindow(self.bridge)
        self.addCleanup(controller.close)
        self.addCleanup(monitor.close)
        monitor.timer.stop()
        monitor.update_gui()
        self.assertEqual(len(monitor.latest),10)
        self.assertEqual(monitor.table.item(0,1).text(), f"{monitor.latest[0]:.3f}")
        self.assertEqual(monitor.table.item(0,2).text(), "0.000")
        self.bridge.unsubscribe(monitor._mailbox)
        while not monitor._mailbox.empty():
            monitor._mailbox.get_nowait()
        held = list(monitor.latest)
        monitor.update_gui()
        self.assertEqual(monitor.latest,held)
        controller.close()
        self.assertTrue(self.bridge.native.running)
        monitor.close()
        self.assertTrue(self.bridge.native.running)
        self.assertEqual(controller.shutdown_error, "")

    def test_magnetic_scaling_targets_and_simultaneous_delivery(self):
        self.wait_packet()
        controller = SimulationControllerWindow(bridge=self.bridge)
        magnetic = SimulationMagneticWindow(self.bridge,controller.context)
        transport = SimulationTransportWindow(self.bridge)
        self.addCleanup(controller.close)
        self.addCleanup(magnetic.close)
        self.addCleanup(transport.close)
        magnetic.timer.stop()
        transport.timer.stop()
        controller.context.set_target(9,123.456,source_mode=ControlMode.MANUAL)
        magnetic.update_gui()
        transport.update_gui()
        self.assertEqual(magnetic.table.item(9,2).text(),"123.460")
        for i,value in enumerate(magnetic.raw_values):
            self.assertAlmostEqual(magnetic.current_values[i],get_scaler().raw_to_eng(TRIM_KEYS[i],value))
        self.assertGreater(len(transport.time_buffer),0)
        self.assertGreater(len(magnetic.time_buffer),0)
        magnetic.toggle_scaling(False)
        time.sleep(.04)
        magnetic.update_gui()
        self.assertEqual(magnetic.current_values,magnetic.raw_values)
        magnetic.close()
        reopened = SimulationMagneticWindow(self.bridge,controller.context)
        self.addCleanup(reopened.close)
        reopened.timer.stop()
        reopened.update_gui()
        self.assertEqual(reopened.table.item(9,2).text(),"123.460")

    def test_source_fields_scaling_and_history_are_recorded(self):
        self.wait_packet()
        window = SimulationSourceWindow(self.bridge)
        self.addCleanup(window.close)
        window.timer.stop()
        packet = window._mailbox.get(timeout=1)
        self.assertEqual(len(packet["source"]),6)
        self.assertEqual(len(packet["extraction_angles"]),6)
        window._mailbox.put_nowait(packet)
        window.update_gui()
        expected = window.scaler.raw_to_eng("coax_a",packet["extraction"][0])
        self.assertAlmostEqual(window.latest_eng[0],expected)
        self.assertGreater(len(window.time_buffer),0)
        self.assertEqual(len(window.top_curves),6)
        self.assertEqual(len(window.bottom_curves),5)
        self.bridge.close()
        rows = self.bridge.recorder.latest(5)
        self.assertTrue(rows)
        for key in ("coax_a","filament_a","q1a_a","esd_in_angle"):
            self.assertTrue(all(row[key] is not None for row in rows),key)

    def test_application_session_owns_all_four_windows_and_flushes(self):
        # Stop this test's standalone bridge before creating the application owner.
        self.bridge.close()
        session = SimulationSession(magnetic=True,transport=True,source=True)
        self.addCleanup(session.shutdown)
        self.assertEqual(len(session.windows),4)
        self.assertTrue(all(window.bridge is session.bridge for window in session.windows))
        session.controller.close()
        self.assertTrue(session.bridge.native.running)
        time.sleep(.05)
        session.shutdown()
        self.assertFalse(session.bridge.native.running)
        self.assertEqual(session.error,"")
        self.assertTrue(session.bridge.recorder.writer.done.is_set())
        session.shutdown() # application finally and aboutToQuit may both call it
        for window in session.windows:
            window.close()


if __name__ == "__main__":
    unittest.main()
