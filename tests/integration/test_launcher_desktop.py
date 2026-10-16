"""Short real desktop navigation/native graphs/PDF check; closes automatically."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.pop("QT_QPA_PLATFORM",None)
os.environ["COMBINATION_RUNTIME_DIR"]=tempfile.mkdtemp(prefix="launcher-desktop-",dir=ROOT/"runtime")
from python.application.paths import configure_environment
configure_environment()
from python.application.native_modules import configure_native_path
configure_native_path()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from python.application.simulation_app import SimulationSession
from python.app.widgets.CstTrendWidget import CstTrendWidget


def main():
    app=QApplication([])
    failures=[]
    report={}
    session=SimulationSession(launcher=True)
    launcher=session.launcher
    output=ROOT/"docs/evidence"

    def exception_hook(kind,value,trace):
        import traceback
        traceback.print_exception(kind,value,trace)
        failures.append(str(value))
        app.quit()
    sys.excepthook=exception_hook

    def capture(window,name,expected):
        charts=[c for c in window.findChildren(CstTrendWidget) if c.isVisible()]
        report[name]={"charts":len(charts),"initialized":sum(c._ready for c in charts),"errors":[c.error for c in charts if c.error]}
        failures.extend(report[name]["errors"])
        if len(charts)!=expected or not all(c._ready for c in charts): failures.append(f"{name}: native chart initialization mismatch")
        if not window.grab().save(str(output/f"launcher_{name}.png")):failures.append(f"{name}: screenshot failed")

    def show_vacuum():
        capture(launcher,"home",0)
        launcher._on_bubble_clicked(4)

    def show_scaling():
        capture(launcher._vac_monitor,"vacuum",2)
        histories=[launcher._vac_monitor.tp1.gauge._native_history,launcher._vac_monitor.tp2.gauge._native_history]
        report["vacuum"]["embedded_histories"]=sum(h.ready for h in histories)
        if not all(h.ready and not h.error for h in histories):failures.append("Embedded native histories failed")
        launcher._vac_monitor.hide()
        launcher._on_bubble_clicked(12)

    def show_history():
        capture(launcher._scale_window,"calibration",1)
        launcher._scale_window.hide()
        launcher._on_bubble_clicked(5)
        viewer=launcher._sqlite_viewer
        viewer.p1.series=["ch1","beam_current"]
        viewer.p2.series=["rf_power_kv"]
        viewer.p3.series=["vac1"]
        QTimer.singleShot(400,viewer.jump_to_latest)

    def export_history():
        viewer=launcher._sqlite_viewer
        if viewer._last_df_shown.empty:failures.append("History did not load recorded samples")
        viewer._add_marker(1)
        capture(viewer,"history",3)
        path=output/"native_history_report.pdf"
        pages=viewer._save_pdf(str(path),[viewer.p1,viewer.p2,viewer.p3],include_markers=True,print_friendly=True)
        report["pdf"]={"pages":pages,"bytes":path.stat().st_size}
        if path.stat().st_size<1000:failures.append("PDF export did not produce a report")

    session.show()
    QTimer.singleShot(700,show_vacuum)
    QTimer.singleShot(2200,show_scaling)
    QTimer.singleShot(3300,show_history)
    QTimer.singleShot(5500,export_history)
    QTimer.singleShot(6500,launcher.close)
    QTimer.singleShot(12000,app.quit)
    app.aboutToQuit.connect(session.shutdown)
    app.exec()
    session.shutdown()
    if session.error:failures.append(session.error)
    report.update(status="failed" if failures else "passed",failures=failures)
    (output/"launcher_desktop.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return int(bool(failures))


if __name__=="__main__":sys.exit(main())
