"""Render CST's original chart in memory, replacing Qt import spellings only."""
from pathlib import Path
import ast
import math
import sys
import types
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage

ROOT=Path(__file__).resolve().parents[2]
CST=ROOT.parent/"Control System Tune 10_15_NewVersion"


def load(name,path):
    module=types.ModuleType(name); module.__file__=str(path); sys.modules[name]=module
    code=path.read_text(encoding="utf-8-sig").replace("PyQt6","PySide6").replace("pyqtSignal","Signal")
    exec(compile(code,str(path),"exec"),module.__dict__)
    return module


if __name__=="__main__":
    app=QApplication([])
    load("controller_theme",CST/"controller_theme.py")
    charts=load("cst_chart_reference",CST/"pid_axis_trend_plot.py")
    # Active PID/GA uses its inline TrendPlot, which adds missing-winner gaps.
    source=CST/"pid_ga_control_tab.py"
    tree=ast.parse(source.read_text(encoding="utf-8-sig"))
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=="TrendPlot")
    module=ast.Module(body=[ast.ImportFrom(module="__future__",names=[ast.alias(name="annotations")],level=0),cls],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(source),"exec"),charts.__dict__)
    x=[i*.1 for i in range(1400)]; target=[5.]*len(x); actual=[5+math.sin(v*.4)*.8 for v in x]
    for third in (False,True):
        widget=charts.TrendPlot(); widget.resize(900,320)
        widget.set_data(x,target,actual,[5+math.sin(v*.4)*.5 for v in x] if third else None)
        image=QImage(widget.size(),QImage.Format.Format_ARGB32); image.fill(0)
        widget.render(image)
        path=ROOT/"docs/evidence"/f"cst_reference_{'three' if third else 'two'}_series.png"
        assert image.save(str(path))
        widget.close()
    print("CST reference chart screenshots rendered; only Qt import spellings adapted in memory")
