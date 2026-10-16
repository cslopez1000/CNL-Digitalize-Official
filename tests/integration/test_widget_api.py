"""Qt host constructor/input contract without showing a window."""
from pathlib import Path
import importlib.util
import sys
from PySide6.QtWidgets import QApplication

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
spec=importlib.util.spec_from_file_location("CstTrendWidget",ROOT/"python/app/widgets/CstTrendWidget.py")
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

if __name__=="__main__":
    app=QApplication([])
    widget=module.CstTrendWidget()
    widget.set_data([0,1,2,3],[1,"bad","3",4],[2,3,4,5])
    assert widget._native.model.rows==[[-3.,1.,2.],[-1.,3.,4.],[0.,4.,5.]]
    widget.clear(); assert widget._native.model.rows==[]
    assert widget.format().majorVersion()==4 and widget.format().minorVersion()==6
    widget.close()
    print("PySide6 host constructor, CST coercion, clear and GL format passed; real window lifecycle not exercised")
