"""Integrated CST controller using a simulation-only native backend."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel
from python.application.paths import runtime_path
from python.adapters.simulation_bridge import SimulationBridge
from python.adapters.native_sequence import native_sequence_classes
from python.app.controls.cst import MagneticFieldControllerWindow as cst_view
from python.app.controls.cst.controller_context import ControlMode
from source.Python.Control.pid_beam_buffer import BEAM_BUFFER

# Reuse the original editors; replace only their timed execution boundary.
NativeSingle, NativeMulti = native_sequence_classes(cst_view.SequenceControlTab, cst_view.MultiTCSequenceTab)
cst_view.SequenceControlTab = NativeSingle
cst_view.MultiTCSequenceTab = NativeMulti


class SimulationControllerWindow(cst_view.MagneticFieldControllerWindow):
    def __init__(self, database_path=None, *, bridge=None, data_queue=None,
                 target_values=None, plot_config=None):
        self._owns_bridge = bridge is None
        self.bridge = bridge or SimulationBridge(database_path or runtime_path("databases/cyclotron_data.db"))
        if self._owns_bridge:
            self.bridge.start()
        self._owns_subscription = data_queue is None
        self._display_queue = self.bridge.subscribe() if data_queue is None else data_queue
        try:
            super().__init__(self.bridge, [0.0]*14 if target_values is None else target_values,
                             plot_config or {"channels":[False]*14,"duration":2,"rate":240},
                             data_queue=self._display_queue)
        except Exception:
            if self._owns_subscription:
                self.bridge.unsubscribe(self._display_queue)
            if self._owns_bridge:
                self.bridge.close()
            raise
        self.context.simulation_bridge = self.bridge
        self.context.mode_changed.connect(self.bridge.set_mode)
        self.bridge.set_mode(self.context.active_mode.value)
        self.setWindowTitle("Cyclotron Controller — C++ Simulation")
        self.simulation_status = QLabel("SIMULATION · C++ acquisition / PID / sequences · no hardware connection")
        self.simulation_status.setStyleSheet("color:#69BDF7; padding:6px; border:1px solid #27323A;")
        self.layout().insertWidget(0, self.simulation_status)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_simulation_status)
        self._status_timer.start(250)
        self._closing = False
        self.shutdown_error = ""
        self._direct_mode = self._beam_input_state.is_direct
        from python.app.widgets.CstTrendWidget import CstTrendWidget
        for chart in self.findChildren(CstTrendWidget):
            chart.render_failed.connect(self._report_graph_error)

    def _report_graph_error(self, error):
        self.simulation_status.setText(f"SIMULATION · native graph error: {error}")

    def set_beam_input_mode(self, mode):
        """Apply CST's switch synchronously to the simulated signal source."""
        changed = super().set_beam_input_mode(mode)
        if changed:
            self.bridge.direct_beam = self._beam_input_state.is_direct
            self.bridge.configure_calibration()
            BEAM_BUFFER.clear()
            self._direct_mode = self.bridge.direct_beam
        return changed

    def _refresh_simulation_status(self):
        direct = self._beam_input_state.is_direct
        if direct != self._direct_mode:
            self.bridge.direct_beam = direct
            try:
                self.bridge.configure_calibration()
                BEAM_BUFFER.clear()
                self._direct_mode = direct
            except Exception as exc:
                self.bridge.error = str(exc)
        storage = self.bridge.recorder.writer.status()
        error = self.bridge.error or storage["error"]
        text = f"SIMULATION · C++ {self.bridge.received_packets} packets · SQLite {storage['written']} batches · {self.context.active_mode.value}"
        if error: text += f" · ERROR: {error}"
        if self.bridge.native.dropped_packets: text += f" · dropped native packets: {self.bridge.native.dropped_packets}"
        self.simulation_status.setText(text)

    def shutdown(self):
        """Cancel UI producers before draining native acquisition and storage."""
        if self._closing:
            return
        self._closing = True
        try:
            for timer in self.findChildren(QTimer):
                timer.stop()
            if getattr(self.pid_tab,"_ga_auto_active",False):
                self.pid_tab._abort_automatic_ga("SIMULATION CLOSED", attempt_restore=False)
            self.pid_tab.stop_pid(reason="SIMULATION CLOSED")
            self.sequence_tab.stop()
            self.multi_sequence_tab.stop()
            tuner = getattr(self.pid_tab, "ga_tuner", None)
            if tuner is not None and hasattr(tuner, "close"):
                tuner.close()
            from python.app.widgets.CstTrendWidget import CstTrendWidget
            for chart in self.findChildren(CstTrendWidget):
                chart.release_native_resources()
        except Exception as exc:
            import sys
            self.shutdown_error = str(exc)
            print(f"Controller cleanup failed: {exc}", file=sys.stderr)
        finally:
            try:
                if self._owns_subscription:
                    self.bridge.unsubscribe(self._display_queue)
                if self._owns_bridge:
                    self.bridge.close()
            except Exception as exc:
                import sys
                self.shutdown_error = "; ".join(part for part in (self.shutdown_error, str(exc)) if part)
                print(f"Simulation shutdown failed: {exc}", file=sys.stderr)

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)
