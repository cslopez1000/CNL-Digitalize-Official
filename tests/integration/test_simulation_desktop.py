"""Short real-desktop CST/native-graph check; closes automatically.

Unlike headless callback tests, this creates real QOpenGLWidget contexts and
captures the integrated controller. It uses a separate simulation database.
"""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
os.environ.pop("QT_QPA_PLATFORM",None)
os.environ["COMBINATION_RUNTIME_DIR"] = tempfile.mkdtemp(prefix="desktop-simulation-",dir=ROOT/"runtime")
from python.application.paths import configure_environment
configure_environment()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from python.application.simulation import SimulationControllerWindow
from python.app.widgets.CstTrendWidget import CstTrendWidget


def main():
    app = QApplication([])
    failures = []
    output = ROOT/"docs/evidence"

    def exception_hook(kind, value, trace):
        import traceback
        failures.append(str(value))
        traceback.print_exception(kind,value,trace)
        app.quit()

    sys.excepthook = exception_hook
    window = SimulationControllerWindow()
    window.resize(1460,1020)
    window.show()
    observations = {}

    def start_preview():
        window.subsystem_tabs.setCurrentIndex(2)
        window.pid_tab.start_pid()

    def capture(name):
        charts = [c for c in window.findChildren(CstTrendWidget) if c.isVisible()]
        observations[name] = {"visible_charts":len(charts), "initialized_charts":sum(c._ready for c in charts),
                              "errors":[c.error for c in charts if c.error]}
        failures.extend(observations[name]["errors"])
        if not charts or not all(c._ready for c in charts):
            failures.append(f"{name}: visible native graph did not initialize")
        if not window.grab().save(str(output/f"simulation_{name}.png")):
            failures.append(f"{name}: screenshot could not be saved")

    def capture_pid():
        capture("pid")
        window.pid_tab.stop_pid(reason="DESKTOP TEST COMPLETE")
        window.subsystem_tabs.setCurrentIndex(1)

    QTimer.singleShot(600,lambda:capture("manual"))
    QTimer.singleShot(800,start_preview)
    QTimer.singleShot(2200,capture_pid)
    QTimer.singleShot(3400,lambda:capture("beam"))
    QTimer.singleShot(4000,window.close)
    QTimer.singleShot(10000,app.quit)
    app.aboutToQuit.connect(window.shutdown)
    app.exec()
    if window.shutdown_error:
        failures.append(window.shutdown_error)
    observations["failures"] = failures
    observations["status"] = "failed" if failures else "passed"
    (output/"simulation_desktop.json").write_text(json.dumps(observations,indent=2),encoding="utf-8")
    print(json.dumps(observations,indent=2))
    return 1 if failures else 0


if __name__=="__main__": sys.exit(main())
