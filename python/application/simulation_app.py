"""One owner for simulation acquisition, recording and all requested CST views."""
import sys
from python.adapters.simulation_bridge import SimulationBridge
from python.application.paths import runtime_path
from python.application.simulation import SimulationControllerWindow


class SimulationSession:
    """Keep backend lifetime independent of any individual display window."""

    def __init__(self, *, magnetic=False, transport=False, source=False, launcher=False):
        self.bridge = SimulationBridge(runtime_path("databases/cyclotron_data.db"))
        self.windows = []
        self.error = ""
        self._closed = False
        try:
            self.bridge.start()
            if launcher:
                from python.application.shell import LauncherWindow
                self.launcher = LauncherWindow(self)
                self.register(self.launcher)
                self.controller = None
                if magnetic:
                    self.launcher.show_magnetic_field_monitoring()
                if transport:
                    self.launcher.show_beam_transport_monitoring()
                if source:
                    self.launcher.show_source_extraction_monitoring()
                return
            self.controller = SimulationControllerWindow(bridge=self.bridge)
            self.windows.append(self.controller)
            if magnetic:
                from python.application.magnetic_monitor import SimulationMagneticWindow
                self.windows.append(SimulationMagneticWindow(self.bridge,self.controller.context))
            if transport:
                from python.application.transport_monitor import SimulationTransportWindow
                self.windows.append(SimulationTransportWindow(self.bridge))
            if source:
                from python.application.source_monitor import SimulationSourceWindow
                self.windows.append(SimulationSourceWindow(self.bridge))
        except Exception:
            self.shutdown()
            raise

    def register(self,window):
        self.windows.append(window)
        window.destroyed.connect(lambda *_:self._forget(window))
        return window

    def _forget(self,window):
        self.windows[:] = [item for item in self.windows if item is not window]

    def show(self):
        for window in self.windows:
            window.show()

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        errors = []
        # Even if one view fails cleanup, stop every producer and flush storage.
        for window in reversed(list(self.windows)):
            try:
                if hasattr(window,"shutdown"):
                    window.shutdown()
                else:
                    from PySide6.QtCore import QTimer
                    from python.app.widgets.CstTrendWidget import CstTrendWidget
                    for timer in window.findChildren(QTimer):
                        timer.stop()
                    for chart in window.findChildren(CstTrendWidget):
                        chart.release_native_resources()
                if getattr(window,"shutdown_error",""):
                    errors.append(window.shutdown_error)
            except Exception as exc:
                errors.append(str(exc))
        try:
            self.bridge.close()
        except Exception as exc:
            errors.append(str(exc))
        self.error = "; ".join(errors)
        if self.error:
            print(f"Simulation session shutdown failed: {self.error}",file=sys.stderr)
