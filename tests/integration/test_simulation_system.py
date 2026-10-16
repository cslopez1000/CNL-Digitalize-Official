"""Integrated CST controller tests without showing a desktop window.

Use native C++ acquisition/PID/sequences and real SQLite. The headless Qt
platform exercises UI callbacks; actual OpenGL rendering has a separate test.
"""
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
RUNTIME = Path(tempfile.mkdtemp(prefix="simulation-tests-", dir=ROOT/"runtime"))
os.environ["COMBINATION_RUNTIME_DIR"] = str(RUNTIME)
from python.application.paths import configure_environment
configure_environment()
from PySide6.QtWidgets import QApplication, QTableWidgetItem
from PySide6.QtTest import QTest
from python.application.simulation import SimulationControllerWindow
from python.app.controls.cst.controller_context import ControlMode
from source.Python.Services.scaling import TRIM_KEYS, get_scaler
from source.Python.Services.beam_cal import beam_cal
from source.Python.Services.beam_range import RangeCodec
import CombinationBackend


def wait_until(predicate, timeout=3):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        QApplication.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


class SimulationSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.database = RUNTIME/f"{self._testMethodName}.db"
        self.window = SimulationControllerWindow(self.database)
        self.addCleanup(self.window.close)
        self.assertTrue(wait_until(lambda: math.isfinite(self.window.context.beam_current())))

    def test_cst_defaults_and_packet_scaling(self):
        w = self.window
        self.assertEqual(w.subsystem_tabs.count(),7)
        self.assertFalse(w.pid_tab.arm_output_check.isChecked())
        self.assertFalse(any(w.context.power_states))
        self.assertFalse(any(w.context.enable_states))
        self.assertTrue(w.bridge.native.running)
        w._poll_actual_data()
        for index, raw in enumerate(w._last_sample["channels"]):
            self.assertAlmostEqual(w.context.actual(index),get_scaler().raw_to_eng(TRIM_KEYS[index],raw))
        self.assertLess(abs(w.bridge.last_packet["_pid_rx_mono"]-time.monotonic()),.3)
        for name in ("calibration.json","beam_cal.json","app_settings.json","alarm_config.json"):
            reference=json.loads((ROOT.parent/"Control System Tune 10_15_NewVersion"/name).read_text(encoding="utf-8"))
            self.assertEqual(json.loads((ROOT/"config"/name).read_text(encoding="utf-8")),reference)

    def test_manual_output_and_cst_rounding(self):
        w = self.window
        w.context.set_power_state(9,True)
        w.context.set_enable_state(9,True)
        value = w.context.set_target(9,123.456,source_mode=ControlMode.MANUAL)
        self.assertEqual(value,123.46)
        expected=get_scaler().eng_to_raw("ch10",value)
        self.assertAlmostEqual(w.bridge.native.sequence_status()["targets"][9],expected)
        self.assertTrue(wait_until(lambda: abs(w.bridge.last_packet["channels"][9]-expected)<max(.00001,abs(expected)*.03),2))
        w.context.set_power_state(9,False)
        self.assertTrue(wait_until(lambda: abs(w.bridge.last_packet["channels"][9])<max(.00001,abs(expected)*.03),2))

    def test_range_readback_and_calibration(self):
        w=self.window
        self.assertTrue(wait_until(lambda:w._beam_base_bitmask is not None))
        w.set_beam_range_mode("digital")
        self.assertTrue(w.request_set_range(1),w._beam_action_status)
        self.assertTrue(wait_until(lambda:w._beam_confirmed_range==1))
        packet=w.bridge.last_packet
        self.assertEqual(packet["beam_range_idx"],1)
        self.assertEqual(packet["bitmask"],RangeCodec.compose(0,1))
        self.assertAlmostEqual(beam_cal.volts_to_nA(packet["beam_current"],1),packet["simulated_beam_nA"],places=8)

    def test_native_sequence_runs_while_gui_is_stalled(self):
        w=self.window
        w.context.set_selected_index(9)
        sequence=w.sequence_tab
        sequence._timer.stop() # progress callbacks cannot execute the rows
        sequence.table.setRowCount(2)
        for row,(at,target) in enumerate(((0,100.123),(.15,150.678))):
            sequence.table.setItem(row,0,QTableWidgetItem(str(at)))
            sequence.table.setItem(row,1,QTableWidgetItem(str(target)))
        sequence.start()
        time.sleep(.3) # native worker continues without Qt events or the GIL
        status=w.bridge.native.sequence_status()
        self.assertEqual(status["state"],"COMPLETED")
        self.assertEqual(status["applied"],2)
        self.assertAlmostEqual(status["targets"][9],get_scaler().eng_to_raw("ch10",150.68))
        sequence._advance()
        self.assertEqual(w.context.target(9),150.68)
        self.assertEqual(w.context.active_mode,ControlMode.MANUAL)

    def test_native_multi_sequence_pause_and_handover(self):
        w=self.window
        sequence=w.multi_sequence_tab
        sequence._timer.stop()
        sequence.table.setRowCount(2)
        for row,at in enumerate((0,.3)):
            sequence.table.setItem(row,0,QTableWidgetItem(str(at)))
            sequence.table.setItem(row,1,QTableWidgetItem(str(20+row*5)))
            sequence.table.setItem(row,10,QTableWidgetItem(str(30+row*5)))
        sequence.start()
        time.sleep(.05)
        sequence.toggle_pause(True)
        time.sleep(.4)
        self.assertEqual(w.bridge.native.sequence_status()["applied"],1)
        sequence.toggle_pause(False)
        time.sleep(.35)
        self.assertEqual(w.bridge.native.sequence_status()["applied"],2)
        sequence._advance()
        self.assertEqual(w.context.target(0),25)
        self.assertEqual(w.context.target(9),35)
        sequence.start()
        w.context.set_mode(ControlMode.MANUAL)
        self.assertEqual(w.bridge.native.sequence_status()["state"],"STOPPED")

    def test_preview_pid_uses_native_math_without_output(self):
        w=self.window
        pid=w.pid_tab
        pid.setpoint_spin.setValue(.7)
        self.assertTrue(wait_until(lambda:math.isfinite(pid._beam_value())))
        before=list(w.bridge.native.sequence_status()["targets"])
        pid.start_pid()
        self.assertTrue(pid._pid_running,pid.pid_status_label.text())
        self.assertTrue(wait_until(lambda: pid.pid.last_result.error_trend!="RESET",3))
        self.assertIsInstance(pid.pid._native,CombinationBackend.AdaptiveDirectionPID)
        self.assertEqual(w.bridge.native.sequence_status()["targets"],before)
        pid.stop_pid(reason="TEST COMPLETE")

    def test_shutdown_flushes_cst_schema(self):
        w=self.window
        self.assertTrue(wait_until(lambda:w.bridge.received_packets>=20))
        w.close()
        self.assertFalse(w.bridge.native.running)
        self.assertFalse(w.shutdown_error)
        with sqlite3.connect(self.database) as connection:
            columns={row[1] for row in connection.execute("PRAGMA table_info(channel_data)")}
            self.assertTrue({"timestamp","ch1","ch12","main_magnet","centering_beam","beam_current","beam_range_idx"}<=columns)
            count=connection.execute("SELECT COUNT(*) FROM channel_data").fetchone()[0]
        self.assertEqual(count,w.bridge.received_packets)

    def test_live_database_reader_uses_independent_connection(self):
        w=self.window
        self.assertTrue(wait_until(lambda:w.bridge.recorder.writer.status()["written"]>0))
        with ThreadPoolExecutor(max_workers=1) as reader:
            rows=reader.submit(w.bridge.recorder.latest,20).result(timeout=3)
        self.assertTrue(rows)
        self.assertEqual([row["timestamp"] for row in rows],sorted((row["timestamp"] for row in rows),reverse=True))
        self.assertTrue(all(math.isfinite(row["ch10"]) for row in rows))
        self.assertTrue(w.bridge.native.running)

    def test_armed_pid_changes_only_enabled_simulated_actuator(self):
        w=self.window
        pid=w.pid_tab
        w.context.set_power_state(9,True)
        w.context.set_enable_state(9,True)
        w.context.set_target(9,100,source_mode=ControlMode.MANUAL)
        pid.setpoint_spin.setValue(2.5)
        pid.deadband_spin.setValue(.01)
        self.assertTrue(wait_until(lambda:math.isfinite(pid._beam_value())))
        pid.arm_output_check.setChecked(True)
        before=w.context.targets_snapshot()
        pid.start_pid()
        self.assertTrue(pid._pid_running,pid.pid_status_label.text())
        self.assertTrue(wait_until(lambda:w.context.target(9)!=before[9],4),pid.pid_status_label.text())
        self.assertEqual(w.context.targets_snapshot()[:9],before[:9])
        self.assertEqual(w.context.targets_snapshot()[10:],before[10:])
        pid.stop_pid(reason="TEST COMPLETE")

    def test_missing_feedback_stops_pid(self):
        w=self.window
        pid=w.pid_tab
        pid.beam_stale_spin.setValue(.3)
        pid.beam_average_spin.setValue(100)
        pid.loop_period_spin.setValue(100)
        self.assertTrue(wait_until(lambda:math.isfinite(pid._beam_value())))
        pid.start_pid()
        self.assertTrue(pid._pid_running)
        w.bridge.native.stop()
        self.assertTrue(wait_until(lambda:not pid._pid_running,2),pid.pid_status_label.text())

    def test_direct_beam_input_preserves_numeric_identity(self):
        w=self.window
        self.assertTrue(w.set_beam_input_mode("other_devices"))
        self.assertTrue(wait_until(lambda:w.bridge.last_packet["simulation_direct_beam"]))
        self.assertTrue(wait_until(lambda:math.isfinite(w.pid_tab._beam_value())))
        packet=w.bridge.last_packet
        self.assertAlmostEqual(packet["beam_current"],packet["simulated_beam_nA"],places=12)
        self.assertTrue(w.set_beam_input_mode("ammeter"))
        self.assertTrue(wait_until(lambda:not w.bridge.last_packet["simulation_direct_beam"]))


if __name__=="__main__": unittest.main(verbosity=2)
