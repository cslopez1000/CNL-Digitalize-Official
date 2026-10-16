"""CST vacuum/beam/RF screen; native data and time-history rendering."""
from PySide6.QtCore import QTimer
from python.app.monitoring.VacuumBeamMonitoringWindow import VacuumBeamMonitoringWindow
from python.app.widgets.CstTrendWidget import CstTrendWidget


class SimulationVacuumWindow(VacuumBeamMonitoringWindow):
    def __init__(self,bridge,data_queue=None):
        self.bridge=bridge
        self._owns_subscription=data_queue is None
        self._mailbox=bridge.subscribe() if data_queue is None else data_queue
        self._closed=False
        try:
            super().__init__(self._mailbox,plot_rate_hz=4,seconds=120,bg_image=None)
        except Exception:
            if self._owns_subscription: bridge.unsubscribe(self._mailbox)
            raise
        self.setWindowTitle(self.windowTitle()+" — SIMULATION")

    def shutdown(self):
        if self._closed: return
        self._closed=True
        for timer in self.findChildren(QTimer): timer.stop()
        if self._owns_subscription: self.bridge.unsubscribe(self._mailbox)
        for chart in self.findChildren(CstTrendWidget): chart.release_native_resources()
        for tile in (self.tp1,self.tp2):
            history=getattr(tile.gauge,"_native_history",None)
            if history is not None:history.close()

    def closeEvent(self,event):
        self.shutdown()
        super().closeEvent(event)
