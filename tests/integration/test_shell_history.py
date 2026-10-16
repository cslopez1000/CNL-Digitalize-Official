"""CST launcher/navigation, configuration, workbook and native history contracts."""
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from threading import Event,Timer

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["COMBINATION_RUNTIME_DIR"]=tempfile.mkdtemp(prefix="shell-tests-",dir=ROOT/"runtime")
from python.application.native_modules import configure_native_path
configure_native_path()
from python.application.paths import configure_environment,runtime_path
configure_environment()
from PySide6 import QtCore,QtWidgets
from PySide6.QtTest import QTest
from python.application.simulation_app import SimulationSession
from python.application.history import HistoryWindow,read_history
from python.application.snapshot_recall import AsyncSnapshotRecallDialog
from python.app.configuration.SettingsDialog import SettingsDialog
from python.app.history.snapshot_save_qt import _scale_signals_if_possible
from source.Python.Data.snapshot_store import save_snapshot,read_snapshots
from source.Python.Services.scaling import get_scaler
from source.Python.Services.alarm import alarm_manager
import CombinationCharts as native
from python.adapters.background_tasks import BackgroundTasks


def wait_until(predicate,timeout=4):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        QtWidgets.QApplication.processEvents()
        if predicate():return True
        QTest.qWait(10)
    return False


class ShellHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.show_patch=patch.object(QtWidgets.QWidget,"show",lambda *_:None)
        self.show_patch.start()
        self.addCleanup(self.show_patch.stop)
        self.session=SimulationSession(launcher=True)
        self.launcher=self.session.launcher
        self.addCleanup(self.session.shutdown)

    def test_all_cst_bubbles_and_navigation_routes(self):
        expected=["Magnetic Field\nMonitoring","Beam Transport\nMonitoring","Beam Source &\nExtraction",
                  "RF Power\nMonitoring","Vac/Beam\nMonitoring","Database\nMonitoring","Settings","Beam Range",
                  "Alarm","Field Ctrl","Snapshot","Recall","Scaling"]
        self.assertEqual([item["title"] for item in self.launcher.bubble_confs],expected)
        actions=["show_magnetic_field_monitoring","show_beam_transport_monitoring","show_source_extraction_monitoring",
                 "show_magnetic_field_controller","show_vacuum_beam_monitoring","show_sqlite_viewer","show_settings_dialog",
                 "show_beam_range_dialog","toggle_alarm","show_magnetic_field_controller","snapshot_save_all",
                 "show_recall_dialog","show_scaling_window"]
        for index,action in enumerate(actions):
            with patch.object(self.launcher,action) as callback:
                self.launcher._on_bubble_clicked(index)
                callback.assert_called_once()
        self.assertTrue(all(Path(item["icon"]).is_file() for item in self.launcher.bubble_confs))

    def test_remaining_windows_share_one_backend_and_close_cleanly(self):
        for method in ("show_magnetic_field_controller","show_magnetic_field_monitoring","show_source_extraction_monitoring",
                       "show_beam_transport_monitoring","show_vacuum_beam_monitoring","show_scaling_window","show_sqlite_viewer"):
            getattr(self.launcher,method)()
        self.assertEqual(len(self.session.windows),8)
        controller=self.launcher.field_controller.mag_controller
        self.assertIs(controller.bridge,self.session.bridge)
        self.launcher.field_controller.close()
        self.assertTrue(self.session.bridge.native.running)
        self.session.shutdown()
        self.assertEqual(self.session.error,"")
        self.assertFalse(self.session.bridge.native.running)

    def test_cst_display_fanout_and_range_command(self):
        self.assertTrue(wait_until(lambda:len(self.session.bridge.last_packet or {})>0))
        self.launcher._pump_data()
        self.assertFalse(self.launcher.mag_queue.empty())
        self.assertFalse(self.launcher.transport_queue.empty())
        self.assertFalse(self.launcher.vac_queue.empty())
        self.launcher.show_beam_range_dialog()
        self.assertEqual(self.launcher._range_dialog.pad._idx,self.session.bridge.last_packet["beam_range_idx"])
        from source.Python.Services.beam_range import RangeCodec
        self.launcher._range_dialog.pad.rangeSelected.emit(1,RangeCodec.compose(0,1))
        self.assertTrue(wait_until(lambda:self.session.bridge.last_packet["beam_range_idx"]==1))

    def test_settings_alarm_persistence_and_toggle(self):
        dialog=SettingsDialog(self.launcher)
        dialog.rf_max.setValue(93)
        dialog.rf_dkv.setValue(4)
        dialog._on_save()
        self.assertEqual(json.loads(Path(os.environ["CNL_APP_SETTINGS"]).read_text())["rf_gauge_max_kv"],93)
        self.assertEqual(json.loads(Path(os.environ["CNL_ALARM_CFG"]).read_text())["rf_dkv"],4)
        alarm_manager.set_active(False)
        self.launcher.toggle_alarm()
        self.assertTrue(alarm_manager.active)
        self.launcher.toggle_alarm()
        self.assertFalse(alarm_manager.active)

    def test_snapshot_round_trip_tc_only_recall(self):
        packet={"channels":[0.]*14,"source":[1.]*6,"extraction":[1.]*6,"transport":[1.]*10}
        scaled=_scale_signals_if_possible(packet)
        path=runtime_path("snapshots/test.xlsx")
        save_snapshot(path,scaled,"first",1000)
        save_snapshot(path,scaled,"second",1001)
        headers,rows=read_snapshots(path)
        self.assertEqual([r["note"] for r in rows],["first","second"])
        self.assertIn("channels",headers)
        self.launcher.target_values[12:14]=[123.,456.]
        self.launcher.apply_magnetic_snapshot({"ch1":12.345})
        self.assertEqual(self.launcher.target_values[0],12.345)
        self.assertEqual(self.launcher.target_values[12:14],[123.,456.])
        dialog=AsyncSnapshotRecallDialog(self.launcher,snapshot_path=str(path))
        self.addCleanup(lambda:dialog.done(0))
        self.assertTrue(wait_until(lambda:len(dialog.rows)==2))
        self.assertIn("second",dialog.combo.itemText(0))

    def test_history_queries_scaling_markers_and_native_zoom(self):
        path=runtime_path("databases/history_fixture.db")
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE channel_data(timestamp REAL,ch1 REAL,beam_current REAL,beam_range_idx INTEGER)")
            connection.executemany("INSERT INTO channel_data VALUES(?,?,?,?)",[(1700000000+i, i*.001,.2,2) for i in range(30)])
        connection.close()
        window=HistoryWindow(str(path))
        self.addCleanup(window.shutdown)
        self.assertTrue(wait_until(lambda:"ch1" in window._db_cols))
        window.p1.series=["ch1","beam_current"]
        window.run_query()
        self.assertTrue(wait_until(lambda:len(window._last_df_shown)==30))
        self.assertEqual(len(window.p1._trace_snapshots),2)
        window.scaling_btn.setChecked(True)
        trace=window.p1._trace_snapshots[0]
        self.assertAlmostEqual(trace.y[0],get_scaler().raw_to_eng("ch1",0))
        window._add_marker(4.4)
        self.assertEqual(window.p1._marker_specs[0].x,4)
        before=window.p1.ax.get_ylim()
        window.p1._zoom_y_axis(1.2)
        after=window.p1.ax.get_ylim()
        self.assertLess(after[1]-after[0],before[1]-before[0])
        window.p1.log_scale_btn.setChecked(True)
        window.p1._toggle_log_scale()
        self.assertGreater(window.p1.ax.get_ylim()[0],0)
        self.assertFalse(hasattr(window.p1.canvas,"fig"))
        metadata,frame=read_history(str(path),["timestamp","ch1"],1700000003,1700000008)
        self.assertEqual(len(frame),6)
        self.assertEqual(metadata["epoch"],"unix")

    def test_native_history_coordinates_and_markers_do_not_change_bounds(self):
        plot=native.CstTrendPlot()
        plot.set_monitor_series(0,[0.,1.],[1.,100.],native.Color(1,0,0),"Test")
        plot.history_log=True
        bounds=plot.history_bounds()
        point=plot.history_point(473.,148.,900.,320.)
        self.assertAlmostEqual(point[0],.5)
        self.assertAlmostEqual(point[1],10.)
        plot.set_history_markers([10000.],["Outside data"],[native.Color(1,0,0)])
        self.assertEqual(plot.history_bounds(),bounds)
        self.assertTrue(all(math.isnan(v) for v in plot.history_point(0,0,900,320)))
        with self.assertRaises(ValueError):plot.zoom_history(0,math.nan)

    def test_failed_snapshot_save_retains_existing_workbook(self):
        path=runtime_path("snapshots/atomic.xlsx")
        save_snapshot(path,{"channels":[1.]*14},"original",1000)
        original=path.read_bytes()
        with patch("source.Python.Data.snapshot_store.append_snapshot_xlsx",side_effect=OSError("test disk failure")):
            with self.assertRaises(OSError):save_snapshot(path,{"channels":[2.]*14},"failed",1001)
        self.assertEqual(path.read_bytes(),original)

    def test_persistent_io_queue_flushes_on_close(self):
        tasks=BackgroundTasks(cancel_on_close=False)
        gate=Event()
        records=[]
        def first():
            gate.wait(2)
            records.append(1)
        tasks.submit("write-1",first)
        tasks.submit("write-2",lambda:records.append(2))
        release=Timer(.1,gate.set)
        release.start()
        tasks.close()
        release.join()
        self.assertEqual(records,[1,2])

    def test_failed_persistent_io_is_reported_on_shutdown(self):
        tasks=BackgroundTasks(cancel_on_close=False)
        def fail():
            raise OSError("test disk failure")
        tasks.submit("write",fail)
        with self.assertRaisesRegex(RuntimeError,"test disk failure"):
            tasks.close()


if __name__=="__main__":unittest.main()
