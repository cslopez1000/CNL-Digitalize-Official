"""Run CST's actual numeric methods against the C++ model, without PyQt6.

Only the Qt constructor and painter are omitted. AST extraction allows this
environment's PySide6 baseline to verify CST code without mixing Qt bindings.
"""
import ast
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
import CombinationCharts as native


def reference_class():
    source = ROOT.parent / "Control System Tune 10_15_NewVersion/pid_ga_control_tab.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TrendPlot")
    cls.bases = []
    cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name not in ("__init__", "paintEvent")]
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), cls], type_ignores=[])
    namespace = {"math": math}
    exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
    return namespace["TrendPlot"]


Reference = reference_class()


class TrendParity(unittest.TestCase):
    def compare(self, x, target, actual, third=None, time_axis=True, window=120, relative=True, limit=600, ylabel="CURRENT (A)", missing=False):
        ref = Reference()
        ref.update = lambda: None
        ref._is_time_axis = time_axis
        ref.rolling_window_s = window
        ref.relative_time = relative and time_axis
        ref.max_display_points = max(50, limit)
        ref.x_axis_label = "TIME (s)" if time_axis else "EVALUATION"
        ref.y_axis_label = ylabel
        ref.allow_missing_target = missing
        ref.set_data(x, target, actual, third)
        model = native.CstTrendModel()
        model.x_label, model.y_label = ref.x_axis_label, ylabel
        model.relative_time, model.rolling_window, model.max_points = ref.relative_time, window, limit
        model.allow_missing_target = missing
        model.set_data(x, target, actual, third)
        expected = list(map(list, zip(ref.x_data, ref.target_data, ref.actual_data, *([ref.third_data] if third is not None else []))))
        self.assertEqual(len(model.rows), len(expected))
        for row, expected_row in zip(model.rows, expected):
            self.assertEqual(len(row), len(expected_row))
            for value, wanted in zip(row, expected_row):
                if math.isnan(wanted): self.assertTrue(math.isnan(value))
                else: self.assertEqual(value, wanted)
        for a, b in zip(model.raw_bounds(), ref._raw_bounds()):
            self.assertAlmostEqual(a, b, places=9)
        b = ref._raw_bounds()
        expected_x = ref._relative_time_axis(b[0], 6) if ref.relative_time else ref._nice_axis(b[0], b[1], 6)
        for axis, expected_axis in ((model.x_axis(), expected_x), (model.y_axis(), ref._nice_axis(b[2], b[3], 5))):
            for a, b in zip((axis.minimum, axis.maximum, axis.step), expected_axis):
                self.assertAlmostEqual(a, b, places=9)
            self.assertEqual(native.CstTrendModel.ticks(axis), ref._tick_values(*expected_axis))
            for value in native.CstTrendModel.ticks(axis):
                self.assertEqual(native.CstTrendModel.format_tick(value, axis.step), ref._format_tick(value, axis.step))

    def test_empty_single_invalid_and_ranges(self):
        for x,a,b in (([],[],[]),([1],[2],[3]),([1,2,3],[1,math.nan,2],[2,3,4]),([0,1,120,121],[0,1,2,3],[4,3,2,1])):
            self.compare(x,a,b)

    def test_decimation_and_epoch_precision(self):
        for n in (50,99,101,601,1001,10000):
            x=[1_800_000_000+i*.01 for i in range(n)]
            self.compare(x,[math.sin(i*.02) for i in range(n)],[math.cos(i*.02) for i in range(n)],limit=50)

    def test_generated_traces(self):
        rng=random.Random(712)
        for time_axis in (False,True):
            for relative in (False,True):
                for third in (False,True):
                    x=[i*.5 for i in range(800)]
                    a=[rng.uniform(-2,20) for _ in x]; b=[rng.uniform(1,30) for _ in x]
                    self.compare(x,a,b,[v*.8 for v in b] if third else None,time_axis=time_axis,relative=relative,ylabel="ABS ERROR")

    def test_constant_and_small_values(self):
        for value in (0,1e-7,.2,1,20000):
            self.compare([0,1,2],[value]*3,[value]*3)

    def test_active_ga_missing_winner_trace(self):
        self.compare([0,1,2,3],[math.nan,math.nan,2,1],[4,3,2,1],time_axis=False,missing=True)
        self.compare([0,1],[math.nan,math.inf],[3,2],time_axis=False,missing=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
