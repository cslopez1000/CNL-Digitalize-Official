"""Shared native acquisition adapter for the original CST magnetic monitor."""
from PySide6.QtCore import QTimer
from python.app.monitoring.MagneticFieldMonitoringWindow import MagneticFieldMonitoringWindow
from python.app.widgets.CstTrendWidget import CstTrendWidget


class SimulationMagneticWindow(MagneticFieldMonitoringWindow):
    def __init__(self, bridge, context, data_queue=None):
        self.bridge, self.context = bridge, context
        self._owns_subscription = data_queue is None
        self._mailbox = bridge.subscribe() if data_queue is None else data_queue
        self._closed = False
        try:
            super().__init__(self._mailbox,context.targets_snapshot(),
                             {"channels":[True]*14})
        except Exception:
            if self._owns_subscription:
                bridge.unsubscribe(self._mailbox)
            raise
        self.setWindowTitle("Magnetic Field Monitoring — SIMULATION")
        for chart in self.findChildren(CstTrendWidget):
            chart.render_failed.connect(self._graph_error)

    def update_gui(self):
        self.target_values = self.context.targets_snapshot()
        super().update_gui()

    def _graph_error(self,error):
        self.header_status.setText(f"Native graph error: {error}")

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        for timer in self.findChildren(QTimer):
            timer.stop()
        if self._owns_subscription:
            self.bridge.unsubscribe(self._mailbox)
        for chart in self.findChildren(CstTrendWidget):
            chart.release_native_resources()

    def closeEvent(self,event):
        self.shutdown()
        super().closeEvent(event)
