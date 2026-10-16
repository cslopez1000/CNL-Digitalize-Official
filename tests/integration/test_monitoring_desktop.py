"""Actual desktop check of CST transport with ten native OpenGL chart contexts."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.pop("QT_QPA_PLATFORM",None)
os.environ["COMBINATION_RUNTIME_DIR"] = tempfile.mkdtemp(prefix="monitor-desktop-",dir=ROOT/"runtime")
from python.application.native_modules import configure_native_path
configure_native_path()
from python.application.paths import configure_environment, runtime_path
configure_environment()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from python.adapters.simulation_bridge import SimulationBridge
from python.application.transport_monitor import SimulationTransportWindow
from python.application.magnetic_monitor import SimulationMagneticWindow
from python.application.simulation import SimulationControllerWindow
from python.app.widgets.CstTrendWidget import CstTrendWidget
from python.application.source_monitor import SimulationSourceWindow


def main():
    app = QApplication([])
    failures = []
    observations = {}
    bridge = SimulationBridge(runtime_path("databases/monitor.db"))
    bridge.start()
    window = SimulationTransportWindow(bridge)
    window.resize(1560,1000)
    window.show()
    controller = SimulationControllerWindow(bridge=bridge)
    magnetic = SimulationMagneticWindow(bridge,controller.context)
    magnetic.resize(1600,950)
    source = SimulationSourceWindow(bridge)
    source.resize(1800,1000)

    def hook(kind,value,trace):
        import traceback
        traceback.print_exception(kind,value,trace)
        failures.append(str(value))
        app.quit()

    sys.excepthook = hook

    def capture():
        charts=window.plot_widgets
        observations.update(visible_charts=len(charts), initialized_charts=sum(c._ready for c in charts),
                            errors=[c.error for c in charts if c.error], samples=len(window.time_buffer))
        failures.extend(observations["errors"])
        if not all(c._ready for c in charts) or not window.time_buffer:
            failures.append("A native chart failed to initialize or telemetry did not arrive")
        if not window.grab().save(str(ROOT/"docs/evidence/transport_monitor.png")):
            failures.append("Screenshot save failed")
        window.hide()
        magnetic.show()

    def capture_magnetic():
        charts=magnetic.findChildren(CstTrendWidget)
        observations["magnetic"]={"charts":len(charts),"initialized":sum(c._ready for c in charts),
                                  "errors":[c.error for c in charts if c.error],"samples":len(magnetic.time_buffer)}
        failures.extend(observations["magnetic"]["errors"])
        if len(charts)!=6 or not all(c._ready for c in charts):
            failures.append("Magnetic native charts did not initialize")
        if not magnetic.grab().save(str(ROOT/"docs/evidence/magnetic_monitor.png")):
            failures.append("Magnetic screenshot save failed")
        magnetic.hide()
        source.show()

    def capture_source():
        charts=source.findChildren(CstTrendWidget)
        observations["source"]={"charts":len(charts),"initialized":sum(c._ready for c in charts),
                                "errors":[c.error for c in charts if c.error],"samples":len(source.time_buffer)}
        failures.extend(observations["source"]["errors"])
        if len(charts)!=11 or not all(c._ready for c in charts):
            failures.append("Source/extraction native charts did not initialize")
        if not source.grab().save(str(ROOT/"docs/evidence/source_monitor.png")):
            failures.append("Source screenshot save failed")
        source.close()
        magnetic.close()
        window.close()
        controller.close()

    QTimer.singleShot(3000,capture)
    QTimer.singleShot(5000,capture_magnetic)
    QTimer.singleShot(7000,capture_source)
    QTimer.singleShot(12000,app.quit)
    app.aboutToQuit.connect(window.shutdown)
    app.aboutToQuit.connect(magnetic.shutdown)
    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(source.shutdown)
    app.exec()
    bridge.close()
    observations.update(failures=failures,status="failed" if failures else "passed")
    (ROOT/"docs/evidence/transport_desktop.json").write_text(json.dumps(observations,indent=2),encoding="utf-8")
    print(json.dumps(observations,indent=2))
    return int(bool(failures))


if __name__=="__main__":
    sys.exit(main())
