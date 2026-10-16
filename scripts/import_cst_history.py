"""Migrate CST history UI, keeping native interactive chart hosts separate."""
import ast
import hashlib
import json
from pathlib import Path
import textwrap

ROOT=Path(__file__).resolve().parents[1]
CST=ROOT.parent/"Control System Tune 10_15_NewVersion"


def main():
    manifest=[]
    for name in ("sqlite_viewer_qt","sqlite_viewer_scaling","sqlite_viewer_report"):
        origin=CST/f"{name}.py"
        code=origin.read_text(encoding="utf-8-sig").replace("PyQt6","PySide6").replace("pyqtSignal","Signal")
        for module in ("sqlite_viewer_scaling","sqlite_viewer_report"):
            code=code.replace(f"from {module} import",f"from python.app.history.{module} import")
        if name=="sqlite_viewer_scaling":
            code=code.replace('importlib.import_module("scaling")','importlib.import_module("source.Python.Services.scaling")')
            code=code.replace('importlib.import_module("beam_cal")','importlib.import_module("source.Python.Services.beam_cal")')
        if name=="sqlite_viewer_qt":
            tree=ast.parse(code)
            pane=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="PlotPane")
            ctor=next(n for n in pane.body if isinstance(n,ast.FunctionDef) and n.name=="__init__")
            lines=code.splitlines(keepends=True)
            head="".join(lines[ctor.lineno:ctor.end_lineno])
            head=head[:head.index('        self.fig = Figure(')]
            head=head.replace("        super().__init__()\n","")
            controls=ROOT/"python/app/history/plot_controls.py"
            if not controls.exists():
                controls.write_text('"""CST plot toolbar/layout, extracted without behavioral edits."""\nfrom PySide6 import QtWidgets\nfrom python.app.history.sqlite_viewer_qt import apply_shadow, NEON_TEXT, PLOT_TITLE_SIZE, ZOOM_FACTOR\n\ndef build_controls(self,title):\n'+textwrap.indent(textwrap.dedent(head),"    ")+"    return head\n",encoding="utf-8")
            resolve=next(n for n in pane.body if isinstance(n,ast.FunctionDef) and n.name=="_resolve_series_name")
            resolver=textwrap.dedent("".join(lines[resolve.lineno-1:resolve.end_lineno]))
            # Remove the original graph classes, while retaining the surrounding UI.
            canvas=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="DroppableCanvas")
            lines[canvas.lineno-1:pane.end_lineno]=[resolver+"\nfrom python.app.history.native_plot_pane import PlotPane\n"]
            code="".join(lines)
            code=code.replace('SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))','from python.application.paths import ROOT\nSCRIPT_DIR = str(ROOT / "assets/ui")')
        destination=ROOT/"python/app/history"/origin.name
        if not destination.exists():
            ast.parse(code)
            destination.write_text(code,encoding="utf-8")
        manifest.append(dict(source_project="CST",source=origin.name,destination=destination.relative_to(ROOT).as_posix(),
                             source_sha256=hashlib.sha256(origin.read_bytes()).hexdigest(),
                             destination_sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
    (ROOT/"docs/evidence/history_migration.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")


if __name__=="__main__": main()
