"""CST public PID API backed by the RI-derived native numerical engine.

The original CST dataclasses and conventional PID are reused. Only the active
adaptive controller delegates to C++; no shadow Python loop executes alongside.
"""
from dataclasses import asdict
import math
import CombinationBackend
from .cst_pid_reference import (PIDGains, PIDLimits, PIDResult, PIDController, AdaptiveDirectionSettings)


class AdaptiveDirectionPIDController:
    def __init__(self, gains=None, limits=None, settings=None):
        self._native = CombinationBackend.AdaptiveDirectionPID()
        self.gains = self._validate_gains(gains or PIDGains())
        self.limits = (limits or PIDLimits(output_min=0.0)).validated()
        self.settings = (settings or AdaptiveDirectionSettings()).validated()
        self._configure()
        self.reset()

    @staticmethod
    def _validate_gains(gains):
        result = gains.validated()
        if min(result.kp, result.ki, result.kd) < 0:
            raise ValueError("Adaptive-direction PID gains Kp, Ki and Kd must be nonnegative")
        return result

    def _configure(self):
        self._native.configure(asdict(self.gains), asdict(self.limits), asdict(self.settings))

    def set_gains(self, gains):
        self.gains = self._validate_gains(gains)
        self._configure()

    def set_limits(self, limits):
        self.limits = limits.validated()
        self._configure()

    def set_settings(self, settings):
        self.settings = settings.validated()
        self._configure()

    def reset(self, *, setpoint=None, measurement=None, direction=None):
        # CST treats invalid optional reset feedback as an unseeded reset.
        try:
            valid = (setpoint is not None and measurement is not None
                     and math.isfinite(float(setpoint)) and math.isfinite(float(measurement)))
        except (TypeError, ValueError):
            valid = False
        self._native.reset(float(setpoint) if valid else None,
                           float(measurement) if valid else None, direction)

    def update(self, setpoint, measurement, dt, *, hold_integrator=False):
        return PIDResult(**self._native.update(float(setpoint), float(measurement),
                                               float(dt), bool(hold_integrator)))

    @property
    def last_result(self):
        return PIDResult(**self._native.last_result)

    @property
    def direction(self):
        return self._native.direction
