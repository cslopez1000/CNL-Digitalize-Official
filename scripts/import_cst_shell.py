"""Read-only CST migration for the launcher, settings and snapshot views.

Existing ports are never overwritten. This records source provenance separately
from the controller and monitoring migration manifests.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
CST = ROOT.parent / "Control System Tune 10_15_NewVersion"
MODULES = {
    "main_control_gui":"python.app.shell.main_control_gui",
    "SmallScreenMagneticBeam":"python.app.controls.cst.SmallScreenMagneticBeam",
    "SettingsDialog":"python.app.configuration.SettingsDialog",
    "ScaleCalWindow":"python.app.configuration.ScaleCalWindow",
    "snapshot_save_qt":"python.app.history.snapshot_save_qt",
    "snapshot_recall_qt":"python.app.history.snapshot_recall_qt",
    "neon_style":"python.app.theme.neon_style",
    "alarm":"source.Python.Services.alarm",
    "scaling":"source.Python.Services.scaling",
    "beam_cal":"source.Python.Services.beam_cal",
    "beam_range":"source.Python.Services.beam_range",
    "app_settings":"source.Python.Services.app_settings",
    "MagneticFieldMonitoringWindow":"python.app.monitoring.MagneticFieldMonitoringWindow",
    "SourceExtractionMonitoringWindow":"python.app.monitoring.SourceExtractionMonitoringWindow",
    "BeamTransportMonitoringWindow":"python.app.monitoring.BeamTransportMonitoringWindow",
}
COPIES = list(MODULES)[:8]


def replace_method(code,name,replacement):
    lines=code.splitlines(keepends=True)
    for cls in ast.parse(code).body:
        if isinstance(cls,ast.ClassDef):
            for node in reversed(cls.body):
                if isinstance(node,ast.FunctionDef) and node.name==name:
                    lines[node.lineno-1:node.end_lineno]=[replacement+"\n"]
    return "".join(lines)


def rewrite(code,name):
    code=code.replace("PyQt6","PySide6").replace("pyqtSignal","Signal").replace("pyqtSlot","Slot")
    for old,new in MODULES.items():
        code=re.sub(rf"(?m)^(\s*)from {old} import ",rf"\1from {new} import ",code)
    if name=="main_control_gui":
        code=code.replace("AUTO →","AUTO ->")
        for module in ("pid_beam_buffer","MagneticFieldControllerWindow","sqlite_viewer_qt","VacuumBeamMonitoringWindow"):
            code=re.sub(rf"(?m)^from {module} import .*\n","",code)
        code=code.replace("import beam_trace; beam_trace.install()", "# Full-rate beam buffering is owned by the shared acquisition collector.")
        code=code.replace("            feed_pid_packet(pkt)","            # Already fed before GUI decimation by SimulationBridge.")
        code=code.replace('HERE = os.path.dirname(os.path.abspath(__file__))','from python.application.paths import ROOT, runtime_path\nHERE = str(ROOT / "assets/ui")')
        code=code.replace('os.path.join(HERE, "snapshots")','str(runtime_path("snapshots"))')
        code=code.replace('DEFAULT_DB_PATH = "cyclotron_data.db"','DEFAULT_DB_PATH = os.environ.get("CNL_DB_PATH", str(runtime_path("databases/cyclotron_data.db")))')
    elif name=="SmallScreenMagneticBeam":
        code=code.replace('from MagneticFieldControllerWindow import MagneticFieldControllerWindow as MagneticOriginal', 'from python.application.shell import create_embedded_controller as MagneticOriginal')
        code=code.replace('        try:\n            mag.setAutoFillBackground(False)', '        self.mag_controller = mag\n\n        try:\n            mag.setAutoFillBackground(False)')
        code=re.sub(r'(?m)^MAG_BG\s*=.*$', 'from python.application.paths import ROOT\nMAG_BG = str(ROOT / "assets/ui/magnetic_bg.png")',code)
        code=re.sub(r'(?m)^BEAM_BG\s*=.*$', 'BEAM_BG = str(ROOT / "assets/ui/beam_range_bg.png")',code)
    elif name=="ScaleCalWindow":
        code=code.replace('from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas','from python.app.widgets.CstCalibrationWidget import CstCalibrationWidget')
        code=code.replace('from matplotlib.figure import Figure','')
        start=code.index('        self.fig = Figure(')
        end=code.index('        rlay.addWidget(self.canvas, 1)',start)
        code=code[:start]+'        self.canvas = CstCalibrationWidget()\n'+code[end:]
        code=replace_method(code,'_refresh_plot','''    def _refresh_plot(self):
        if not hasattr(self,"canvas"):
            return
        key = self._current_key()
        inverse = self.tabs.currentIndex() == 1
        points = self._parse_text_points((self.te_e2r if inverse else self.te_r2e).toPlainText())
        title = f"{label_for(key)} — {'Eng → Raw' if inverse else 'Raw → Eng'}"
        self.canvas.set_curve(title,points,inverse)
''')
    return code


def main():
    manifest=[]
    for module in COPIES:
        origin=CST/f"{module}.py"
        destination=ROOT.joinpath(*MODULES[module].split('.')).with_suffix('.py')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists():
            code=rewrite(origin.read_text(encoding="utf-8-sig"),module)
            ast.parse(code)
            destination.write_text(code,encoding="utf-8")
        manifest.append(dict(source_project="CST",source=origin.name,destination=destination.relative_to(ROOT).as_posix(),
                             source_sha256=hashlib.sha256(origin.read_bytes()).hexdigest(),
                             destination_sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
    for icon in (CST/"icons").glob("icon_*_3d.png"):
        destination=ROOT/"assets/ui/icons"/icon.name
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists(): shutil.copyfile(icon,destination)
    for name in ("magnetic_bg.png","beam_range_bg.png"):
        if (CST/name).exists() and not (ROOT/"assets/ui"/name).exists():
            shutil.copyfile(CST/name,ROOT/"assets/ui"/name)
    (ROOT/"docs/evidence/shell_migration.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
