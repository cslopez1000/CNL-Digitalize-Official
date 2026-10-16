"""Migrate CST monitoring views without changing the original project.

Re-running refuses to overwrite integrated views. Source hashes record which
version was selected; application code never imports the original project.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CST = ROOT.parent / "Control System Tune 10_15_NewVersion"


def transport_source(source):
    code = source.replace("PyQt6", "PySide6")
    lines = code.splitlines(keepends=True)
    helpers = {"style_plot_tesla", "add_tesla_series"}
    nodes = [n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name in helpers]
    for node in reversed(nodes):
        lines[node.lineno-1:node.end_lineno] = []
    code = "".join(lines).replace("import pyqtgraph as pg", "from python.app.widgets.CstTransportWidget import CstTransportWidget, NativeShadow\nfrom python.application.paths import ROOT")
    code = code.replace("pg.setConfigOptions(antialias=True)", "")
    code = code.replace("style_plot_cyberpunk = style_plot_tesla", "").replace("add_cyberpunk_series = add_tesla_series", "")
    start = code.index("            pw = pg.PlotWidget()")
    end = code.index("            self.plot_widgets.append(pw)", start)
    code = code[:start] + '''            pw = CstTransportWidget(name, neon_color(i), self.history_seconds)
            pw.setToolTip("Right edge = current monitor receipt time. No samples are invented while data are missing.")
            glow, curve = NativeShadow(), pw
''' + code[end:]
    code = code.replace('Path(__file__).resolve().with_name(filename)', 'ROOT / "assets/ui" / filename')
    return code


def main():
    manifest = []
    for name, rewrite in (("BeamTransportMonitoringWindow.py",transport_source),
                          ("MagneticFieldMonitoringWindow.py",magnetic_source),
                          ("SourceExtractionMonitoringWindow.py",source_source),
                          ("VacuumBeamMonitoringWindow.py",vacuum_source)):
        destination = ROOT / "python/app/monitoring" / name
        original = (CST / name).read_bytes()
        if not destination.exists():
            code = rewrite(original.decode("utf-8-sig"))
            ast.parse(code)
            destination.write_text(code, encoding="utf-8")
        manifest.append({"source_project": "CST", "source": name,
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "destination": destination.relative_to(ROOT).as_posix(),
                "destination_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "changes": "PySide6/package imports; absolute logo path; native C++ chart hosts. Original layout, buffering, scaling, units, readout/error and stale behavior retained."})
    (ROOT / "docs/evidence/monitor_migration.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def magnetic_source(source):
    code = source.replace("PyQt6", "PySide6").replace("pyqtSignal", "Signal")
    lines = code.splitlines(keepends=True)
    nodes = [n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name in {"style_plot_tesla","add_tesla_series"}]
    for node in reversed(nodes):
        lines[node.lineno-1:node.end_lineno] = []
    code = "".join(lines).replace("import pyqtgraph as pg", "from python.app.widgets.CstMagneticWidget import CstMagneticWidget\nfrom python.app.widgets.CstTransportWidget import NativeShadow\nfrom python.application.paths import ROOT")
    code = code.replace("from scaling import", "from source.Python.Services.scaling import").replace("from app_settings import", "from source.Python.Services.app_settings import")
    code = code.replace("pg.setConfigOptions(antialias=True)", "")
    start=code.index("            plot = pg.PlotWidget()")
    end=code.index("            for ch in self.plot_groups[group_idx]:",start)
    code=code[:start]+"            plot = CstMagneticWidget(titles[group_idx])\n\n"+code[end:]
    code=code.replace("glow, line = add_tesla_series(plot, TC_COLORS[ch], CHANNEL_LABELS[ch])", "glow, line = NativeShadow(), plot.add_series(TC_COLORS[ch], CHANNEL_LABELS[ch])")
    start=code.index("        self.trim_bar_plot = pg.PlotWidget()")
    end=code.index("        lay.addWidget(self.trim_bar_plot)",start)
    code=code[:start]+'''        self.trim_bar_plot = CstMagneticWidget(kind=2)
        self.trim_bars = [(ch, self.trim_bar_plot.add_series(TC_COLORS[ch])) for ch in range(NUM_TRIM)]

'''+code[end:]
    start=code.index("        spark = pg.PlotWidget()")
    end=code.index("        lay.addWidget(spark)",start)
    code=code[:start]+'''        spark = CstMagneticWidget(kind=1)
        spark.setFixedHeight(38)
        curve = spark.add_series(BLUE)
'''+code[end:]
    code=code.replace('Path(__file__).with_name("cnl_logo.png")','ROOT / "assets/ui/cnl_logo.png"')
    return code.replace('        self.heartbeat = None', '''        self.heartbeat = None
        # CST callbacks still use this indicator after its visible layout was removed.
        self.scaling_status = QLabel(self)
        self.scaling_status.hide()''')


def source_source(source):
    code=source.replace("PyQt6","PySide6").replace("from scaling import", "from source.Python.Services.scaling import")
    code=code.replace("import pyqtgraph as pg", "from python.app.widgets.CstMagneticWidget import CstMagneticWidget\nfrom python.app.widgets.CstTransportWidget import NativeShadow\nfrom python.application.paths import ROOT")
    code=code.replace("pg.setConfigOptions(antialias=True)", "")
    code=code.replace('LOGO_PATH = os.path.join(HERE, "CNL_logo.png")','LOGO_PATH = str(ROOT / "assets/ui/cnl_logo.png")')
    lines=code.splitlines(keepends=True)
    nodes=[n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name in {"style_plot_tesla","add_tesla_series"}]
    for node in reversed(nodes):
        lines[node.lineno-1:node.end_lineno]=[]
    code="".join(lines)
    for section, title, color in (("EXTRACTION_PLOTS","RAW_LABELS[key]","C_EXTR"),("SOURCE_PLOTS","title","C_SRC")):
        loop=code.index(f"        for pos, key in enumerate({section}):")
        start=code.index("            pw = pg.PlotWidget()",loop)
        end=code.index("            card = TeslaPlotCard(pw)",start)
        code=code[:start]+f'''            pw = CstMagneticWidget({title},kind=3)
            pw.setMinimumHeight(130)
            shadow_curve, main_curve = NativeShadow(), pw.add_series({color})

'''+code[end:]
    return code


def vacuum_source(source):
    code=source.replace("PyQt6","PySide6").replace("pyqtSignal","Signal").replace("pyqtProperty","Property")
    code=code.replace('        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 230), 2.0, cap=QtCore.Qt.PenCapStyle.RoundCap))',
        '        needle_pen=QtGui.QPen(QtGui.QColor(255,255,255,230),2.0)\n        needle_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)\n        p.setPen(needle_pen)')
    for name in ("scaling","beam_cal","app_settings"):
        code=code.replace(f"from {name} import",f"from source.Python.Services.{name} import")
    lines=code.splitlines(keepends=True)
    cls=next(n for n in ast.parse(code).body if isinstance(n,ast.ClassDef) and n.name=="TimeSeriesPlot")
    lines[cls.lineno-1:cls.end_lineno]=["from python.app.widgets.CstVacuumWidget import CstVacuumWidget as TimeSeriesPlot\n"]
    code="".join(lines)
    tree=ast.parse(code)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="LogVacuumGauge")
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="_draw_history")
    lines=code.splitlines(keepends=True)
    lines[method.lineno-1:method.end_lineno]=['''    def _draw_history(self,painter,cx,cy,radius):
        # Keep CST's embedded-history rectangle; native code maps/logs/draws.
        if not hasattr(self,"_native_history"):
            from python.app.widgets.NativeVacuumHistory import NativeVacuumHistory
            self._native_history = NativeVacuumHistory(self)
        rect=QtCore.QRectF(cx-radius*.58,cy-radius*.60,radius*1.16,radius*.245+20)
        image=self._native_history.render(rect.width(),rect.height(),self.devicePixelRatioF(),
                                          self._history,self._display_color(),self.history_seconds)
        painter.drawImage(rect,image)
''']
    return "".join(lines)


if __name__ == "__main__":
    main()
