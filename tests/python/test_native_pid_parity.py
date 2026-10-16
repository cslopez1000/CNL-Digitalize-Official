"""Compare native adaptive PID with the unmodified active CST reference."""
from dataclasses import asdict
import importlib.util
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
from source.Python.Control.pid_adapter import AdaptiveDirectionPIDController as NativePID
from source.Python.Control.cst_pid_reference import PIDGains, PIDLimits, AdaptiveDirectionSettings

path = ROOT.parent/"Control System Tune 10_15_NewVersion/pid_controller.py"
spec = importlib.util.spec_from_file_location("cst_pid_independent_reference", path)
reference = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reference
spec.loader.exec_module(reference)


class NativePidParity(unittest.TestCase):
    def exercise(self, each_update):
        rng = random.Random(284)
        config = dict(deadband=.2, max_control_dt=.3, direction_each_update=each_update,
                      reset_integral_on_direction_change=False, direction_check_interval=.3)
        native = NativePID(PIDGains(.8,.1,.1), PIDLimits(output_max=4,integral_max=2), AdaptiveDirectionSettings(**config))
        python = reference.AdaptiveDirectionPIDController(reference.PIDGains(.8,.1,.1),
                   reference.PIDLimits(output_max=4,integral_max=2), reference.AdaptiveDirectionSettings(**config))
        for index in range(1200):
            measurement = 4+math.sin(index*.07)*2+rng.uniform(-.02,.02)
            dt = (0.3,0.2,.6,1.5)[index%4]
            setpoint = 4 if index<600 else 4.5
            if index in (300,800):
                native.reset(direction=-1); python.reset(direction=-1)
            a = native.update(setpoint,measurement,dt,hold_integrator=index%19==0)
            b = python.update(setpoint,measurement,dt,hold_integrator=index%19==0)
            for key,value in asdict(b).items():
                actual = getattr(a,key)
                if isinstance(value,float):
                    self.assertTrue(math.isclose(value,actual,rel_tol=1e-9,abs_tol=1e-9),f"{index}: {key}: native={actual}, CST={value}")
                else: self.assertEqual(actual,value,f"{index}: {key}")

    def test_active_per_average_mode(self): self.exercise(True)
    def test_legacy_window_mode(self): self.exercise(False)

    def test_validation_and_seeded_reset(self):
        with self.assertRaises(ValueError): NativePID(PIDGains(-1,0,0))
        pid = NativePID()
        with self.assertRaises(ValueError):
            pid._native.configure(asdict(PIDGains(-1,0,0)),asdict(pid.limits),asdict(pid.settings))
        for value in (math.nan,math.inf):
            with self.assertRaises(ValueError): pid.update(1,value,.1)
        for dt in (0,-1):
            with self.assertRaises(ValueError): pid.update(1,0,dt)
        pid.reset(setpoint=2,measurement=1,direction=-1)
        self.assertEqual(pid.direction,-1)
        self.assertEqual(pid.last_result.error_trend,"RESET")


if __name__=="__main__": unittest.main(verbosity=2)
