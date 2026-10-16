"""Launch the integrated simulation, or the independent native graph preview."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def load_graphs(require_launcher=True):
    from python.application.native_modules import configure_native_path
    configure_native_path()
    try:
        import CombinationCharts
        import CombinationBackend
        import PySide6
    except ImportError as exc:
        raise RuntimeError("Dependencies/native module missing or incompatible. Run scripts/install.ps1 or bash scripts/install_ubuntu.sh.") from exc
    required=("render_history","render_vacuum","render_calibration")
    if (not all(hasattr(CombinationCharts.CstTrendPlot,name) for name in required)
            or not hasattr(CombinationCharts,"clear_transparent_frame")):
        raise RuntimeError("Native graphs are outdated. Rebuild with scripts/install.ps1 or bash scripts/install_ubuntu.sh.")
    if require_launcher:
        from importlib.util import find_spec
        missing=[name for name in ("openpyxl","numpy","pandas","matplotlib") if find_spec(name) is None]
        if missing:
            raise RuntimeError(f"Launcher dependencies missing: {', '.join(missing)}. Re-run the installer.")
    return CombinationCharts, PySide6


def main():
    parser = argparse.ArgumentParser(description="CST controller with a simulation-only C++ backend")
    parser.add_argument("--check", action="store_true", help="check module/dependency imports without opening a window")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--simulation", "-Simulation", action="store_true", help="launch the integrated simulation (default)")
    mode.add_argument("--zmq", "-ZMQ", action="store_true", help="request ZMQ (not yet implemented in Combination; exits with an error)")
    view = parser.add_mutually_exclusive_group()
    view.add_argument("--preview", action="store_true", help="launch only the independent native chart preview")
    view.add_argument("--controller", action="store_true", help="open the standalone controller instead of CST's launcher")
    parser.add_argument("--transport", action="store_true", help="also open CST beam transport monitoring against the same native simulation")
    parser.add_argument("--magnetic", action="store_true", help="also open CST magnetic monitoring against the same native simulation")
    parser.add_argument("--source", action="store_true", help="also open CST source/extraction monitoring against the same native simulation")
    args = parser.parse_args()
    if args.zmq:
        parser.error("Combination's ZMQ backend is not implemented yet. No connection was started. Use -Simulation for the integrated CST application; the original RecurseIntall main.py supports -ZMQ.")
    if args.preview and (args.magnetic or args.transport or args.source):
        parser.error("Monitoring options require the integrated simulation, not --preview")
    try:
        native, qt = load_graphs(require_launcher=not args.preview)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.check:
        print(f"Ready: Python {sys.version.split()[0]}, PySide6 {qt.__version__}, native graphs {native.__file__}")
        print("Ready: native simulation backend and CST launcher/navigation. Hardware is unavailable; --controller opens the standalone controller.")
        return 0

    if not args.preview:
        from python.application.paths import configure_environment
        configure_environment()
        from PySide6.QtWidgets import QApplication
        from python.application.simulation_app import SimulationSession
        app = QApplication(sys.argv[:1])
        session = SimulationSession(magnetic=args.magnetic,transport=args.transport,source=args.source,
                                    launcher=not args.controller)
        app.aboutToQuit.connect(session.shutdown)
        try:
            session.show()
            result = app.exec()
        finally:
            session.shutdown()
        return 1 if session.error else result

    import math
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
    from python.app.widgets.CstTrendWidget import CstTrendWidget

    app = QApplication(sys.argv[:1])
    window = QMainWindow()
    window.setWindowTitle("Combination — CST native chart preview")
    window.resize(1100, 780)
    container = QWidget()
    layout = QVBoxLayout(container)
    label = QLabel("CST chart style · C++ / OpenGL backend\nSimulated preview — full UI/control/database migration pending")
    layout.addWidget(label)
    beam = CstTrendWidget(y_axis_label="BEAM CURRENT (nA)")
    coil = CstTrendWidget(y_axis_label="CURRENT (A)")
    layout.addWidget(beam)
    layout.addWidget(coil)
    status = QLabel("Simulated data only")
    for chart in (beam, coil):
        chart.render_failed.connect(lambda error: status.setText(f"OpenGL error: {error}"))
    layout.addWidget(status)
    pause = QPushButton("Pause")
    layout.addWidget(pause)
    window.setCentralWidget(container)
    window.setStyleSheet("QWidget { background:#0B1116; color:#E8EDF0; font-family:'Segoe UI'; } QPushButton { background:#0D151B; border:1px solid #27323A; padding:8px; }")
    clock = [140.0]

    def update():
        clock[0] += .1
        x = [clock[0] - (1399-i)*.1 for i in range(1400)]
        raw = [5 + .5*math.sin(v*.4) + .15*math.sin(v*8) for v in x]
        average = [5 + .5*math.sin(v*.4) for v in x]
        beam.set_data(x, [5.]*len(x), raw, average)
        coil.set_data(x, [80.]*len(x), [80 + 2*math.sin(v*.2) for v in x])

    timer = QTimer(container)
    timer.setInterval(100)
    timer.timeout.connect(update)

    def toggle():
        if timer.isActive(): timer.stop(); pause.setText("Resume")
        else: timer.start(); pause.setText("Pause")

    pause.clicked.connect(toggle)
    app.aboutToQuit.connect(beam.release_native_resources)
    app.aboutToQuit.connect(coil.release_native_resources)
    update()
    timer.start()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
