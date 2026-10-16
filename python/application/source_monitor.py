"""Reused CST source/extraction monitor; shared native simulation subscriber."""
from PySide6.QtCore import QTimer
from python.app.monitoring.SourceExtractionMonitoringWindow import SourceExtractionMonitoringWindow
from python.app.widgets.CstTrendWidget import CstTrendWidget


class SimulationSourceWindow(SourceExtractionMonitoringWindow):
    def __init__(self,bridge,data_queue=None):
        self.bridge = bridge
        self._owns_subscription = data_queue is None
        self._mailbox = bridge.subscribe() if data_queue is None else data_queue
        self._closed = False
        try:
            super().__init__(self._mailbox,plot_rate_hz=4,seconds=60,bg_image=None)
        except Exception:
            if self._owns_subscription:
                bridge.unsubscribe(self._mailbox)
            raise
        self.setWindowTitle("CNL — Source & Extraction Monitoring — SIMULATION")
        self.graph_errors = []
        for chart in self.findChildren(CstTrendWidget):
            chart.render_failed.connect(self.graph_errors.append)

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
