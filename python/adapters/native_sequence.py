"""Reuse CST sequence editors/validation; move timed row execution to C++.

Qt timers refresh progress only. The native acquisition worker applies rows
even when the UI is busy. Power/enable masks remain unchanged, as in CST.
"""
import math
from source.Python.Services.scaling import TRIM_KEYS, get_scaler
from python.app.controls.cst.controller_context import ControlMode


class NativeSequenceExecution:
    """Mixin placed before CST's single/multi sequence view in the MRO."""
    native_mode = ControlMode.SEQUENCE

    def _backend(self):
        return getattr(self.context, "simulation_bridge", None)

    def start(self):
        bridge = self._backend()
        if bridge is None:
            self.status_label.setText("SIMULATION BACKEND NOT CONNECTED")
            return
        try:
            rows = self._read_rows()
            if not rows:
                self.status_label.setText("SEQUENCE EMPTY")
                return
            channel = self.context.selected_index
            engineering_rows = [(at, {channel: values} if self.native_mode == ControlMode.SEQUENCE else values) for at, values in rows]
            self._engineering_rows = []
            native_rows = []
            scaler = get_scaler()
            for at, updates in engineering_rows:
                if not math.isfinite(at):
                    raise ValueError("Sequence time must be finite")
                clamped = {}
                for index, target in updates.items():
                    if not math.isfinite(target):
                        raise ValueError("Sequence target must be finite")
                    clamped[index] = round(self.context.clamp_target(index, target), 2)
                self._engineering_rows.append(clamped)
                native_rows.append((at, {index: scaler.eng_to_raw(TRIM_KEYS[index], value) for index, value in clamped.items()}))
            self.context.set_mode(self.native_mode)
            bridge.native.start_sequence(native_rows, self.native_mode.value)
            self._job = {"next": 0, "rows": rows, "channel": channel}
            self._paused = False
            self.pause_button.setChecked(False)
            self.pause_button.setText("PAUSE")
            self.status_label.setText(f"RUNNING — 0 / {len(rows)}")
        except (ValueError, RuntimeError) as exc:
            self.status_label.setText(str(exc).upper())

    def toggle_pause(self, checked):
        if self._job is None:
            self.pause_button.setChecked(False)
            return
        self._backend().native.pause_sequence(bool(checked))
        self._paused = bool(checked)
        self.pause_button.setText("RESUME" if checked else "PAUSE")
        self.status_label.setText("PAUSED" if checked else "RUNNING")

    def stop(self, *, restore_manual_mode=True):
        if self._job is not None and self._backend() is not None:
            self._backend().native.stop_sequence()
        super().stop(restore_manual_mode=restore_manual_mode)

    def _advance(self):
        if self._job is None:
            return
        status = self._backend().native.sequence_status()
        # Update CST's displayed engineering targets with the exact row values;
        # inverse calibration need not be lossless and must not reinterpret them.
        for row in self._engineering_rows[self._job["next"]:status["applied"]]:
            self.context.set_targets(row, send=False, source_mode=self.native_mode)
        self._job["next"] = status["applied"]
        self.status_label.setText(f"{status['state']} — {status['applied']} / {status['total']} — t = {status['elapsed']:.2f} s")
        if status["state"] == "COMPLETED":
            self._job = None
            self.context.set_mode(ControlMode.MANUAL)


def native_sequence_classes(single_view, multi_view):
    class NativeSingleSequence(NativeSequenceExecution, single_view):
        native_mode = ControlMode.SEQUENCE

    class NativeMultiSequence(NativeSequenceExecution, multi_view):
        native_mode = ControlMode.MULTI_SEQUENCE

    return NativeSingleSequence, NativeMultiSequence
