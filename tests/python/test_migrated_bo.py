"""Reuse CST's BO suite against the migrated modules, not the originals."""
import ast
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
source = ROOT.parent/"Control System Tune 10_15_NewVersion/BO/test_bo_integration.py"
tree = ast.parse(source.read_text(encoding="utf-8-sig"))
mapping = {
    "ga_pid_tuner":"source.Python.Optimization.cst_ga",
    "pid_controller":"source.Python.Control.pid_adapter",
    "BO.bo_pid_adapter":"python.app.controls.cst.bo.bo_pid_adapter",
    "BO.bo_trial_runner":"python.app.controls.cst.bo.bo_trial_runner",
    "BO.optimization":"source.Python.Optimization.bo",
}
for node in ast.walk(tree):
    if isinstance(node,ast.ImportFrom) and node.module in mapping:
        node.module=mapping[node.module]
    if isinstance(node,ast.Constant) and isinstance(node.value,str):
        for old,new in mapping.items():
            if node.value.startswith(old+"."):
                node.value=new+node.value[len(old):]
                break
    if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=="source" for target in node.targets):
        node.value=ast.Call(func=ast.Name(id="Path",ctx=ast.Load()),args=[ast.Constant(str(ROOT/"python/app/controls/cst/pid_ga_control_tab.py"))],keywords=[])
module=types.ModuleType("migrated_bo_reference_tests")
module.__file__=str(source)
sys.modules[module.__name__]=module
exec(compile(ast.fix_missing_locations(tree),str(source),"exec"),module.__dict__)

if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    sys.exit(0 if result.wasSuccessful() else 1)
