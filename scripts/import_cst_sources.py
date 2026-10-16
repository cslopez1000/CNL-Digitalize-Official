"""Import selected existing CST modules with explicit package/Qt adjustments.

This is a migration utility, not a runtime loader. It refuses to overwrite a
ported file so subsequent integration edits are never lost. Original CST files
are read only. The manifest records exactly which source each file came from.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CST = ROOT.parent / "Control System Tune 10_15_NewVersion"
MODULES = {
    "MagneticFieldControllerWindow": "python.app.controls.cst.MagneticFieldControllerWindow",
    "controller_context": "python.app.controls.cst.controller_context",
    "controller_theme": "python.app.controls.cst.controller_theme",
    "manual_control_tab": "python.app.controls.cst.manual_control_tab",
    "sequence_control_tab": "python.app.controls.cst.sequence_control_tab",
    "multi_tc_sequence_tab": "python.app.controls.cst.multi_tc_sequence_tab",
    "pid_ga_control_tab": "python.app.controls.cst.pid_ga_control_tab",
    "beam_range": "source.Python.Services.beam_range",
    "beam_cal": "source.Python.Services.beam_cal",
    "scaling": "source.Python.Services.scaling",
    "app_settings": "source.Python.Services.app_settings",
    "pid_beam_buffer": "source.Python.Control.pid_beam_buffer",
    "pid_decision_log": "source.Python.Data.pid_decision_log",
    "sqlite_logger": "source.Python.Data.cst_schema",
    "ga_pid_tuner": "source.Python.Optimization.cst_ga",
    "ga_test_runner": "source.Python.Automation.ga_evaluation",
    "ga_recovery_manager": "source.Python.Automation.ga_recovery",
    "pid_controller": "source.Python.Control.pid_adapter",
}


def replace_class(code, name, replacement):
    cls = next(node for node in ast.parse(code).body if isinstance(node, ast.ClassDef) and node.name == name)
    lines = code.splitlines(keepends=True)
    lines[cls.lineno-1:cls.end_lineno] = [replacement + "\n"]
    return "".join(lines)


def rewrite(code, origin):
    code = code.replace("PyQt6", "PySide6").replace("pyqtSignal", "Signal").replace("pyqtSlot", "Slot")
    for old, new in MODULES.items():
        code = re.sub(rf"(?m)^(\s*)from {re.escape(old)} import ", rf"\1from {new} import ", code)
    code = re.sub(r"(?m)^(\s*)from BO\.optimization", r"\1from source.Python.Optimization.bo", code)
    code = re.sub(r"(?m)^(\s*)from BO\.", r"\1from python.app.controls.cst.bo.", code)
    if origin.startswith("BO/"):
        code = code.replace("from .optimization import ", "from source.Python.Optimization.bo import ")
    if origin == "pid_ga_control_tab.py":
        code = replace_class(code, "TrendPlot", "from python.app.widgets.CstTrendWidget import CstTrendWidget as TrendPlot")
        code = replace_class(code, "PIDGainRadar", "from python.app.widgets.CstGainWidget import CstGainWidget as PIDGainRadar")
        code = code.replace("from __future__ import annotations", "from __future__ import annotations\nfrom python.application.paths import runtime_path")
        code = code.replace('Path(__file__).resolve().parent / "pid_decision_logs"', 'runtime_path("logs/pid_decisions")')
        code = code.replace('Path(__file__).resolve().parent / strategy / run_name', 'runtime_path("exports") / strategy / run_name')
    if origin == "controller_theme.py":
        code = replace_class(code, "TrendPlot", "from python.app.widgets.CstManualWidget import CstManualWidget as TrendPlot")
    if origin == "MagneticFieldControllerWindow.py":
        code = replace_class(code, "_ControllerBeamPlot", "from python.app.widgets.CstBeamWidget import CstBeamWidget as _ControllerBeamPlot")
        code = code.replace("here = os.path.dirname(os.path.abspath(__file__))", 'from python.application.paths import ROOT\n        here = str(ROOT / "assets/ui")')
    return code


def main():
    copies = [(f"{old}.py", ROOT.joinpath(*new.split('.')).with_suffix('.py')) for old,new in MODULES.items() if old != "pid_controller"]
    copies.append(("pid_controller.py", ROOT/"source/Python/Control/cst_pid_reference.py"))
    for path in (CST/"BO").rglob("*.py"):
        if path.name.startswith("test_"): continue
        relative = path.relative_to(CST).as_posix()
        destination = ROOT/"source/Python/Optimization/bo"/path.relative_to(CST/"BO/optimization") if "optimization" in path.parts else ROOT/"python/app/controls/cst/bo"/path.name
        copies.append((relative, destination))
    manifest = []
    for origin, destination in copies:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = CST/origin
        if not destination.exists():
            code = rewrite(source.read_text(encoding="utf-8-sig"), origin)
            destination.write_text(code, encoding="utf-8")
        manifest.append({"source_project":"CST", "source":origin, "destination":destination.relative_to(ROOT).as_posix(),
                         "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                         "destination_sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
                         "changes":"Qt binding/package imports; native trend alias and runtime paths where applicable"})
    for name in ("calibration.json", "beam_cal.json", "app_settings.json", "alarm_config.json"):
        destination=ROOT/"config"/name
        if not destination.exists(): destination.write_bytes((CST/name).read_bytes())
    for name in ("cnl_logo.png",):
        destination=ROOT/"assets/ui"/name
        if not destination.exists(): destination.write_bytes((CST/name).read_bytes())
    for directory in (ROOT/"python", ROOT/"source/Python"):
        for folder in [directory,*[p for p in directory.rglob('*') if p.is_dir()]]:
            (folder/"__init__.py").touch(exist_ok=True)
    (ROOT/"source/__init__.py").touch(exist_ok=True)
    (ROOT/"docs/evidence/cst_migration_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Imported/retained {len(manifest)} CST modules; no existing port was overwritten")


if __name__=="__main__": main()
