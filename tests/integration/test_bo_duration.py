"""Verify BO duration reaches the shared evaluator without changing GA settings."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from python.application.native_modules import configure_native_path
configure_native_path()
from python.app.controls.cst.bo.bo_control_tab import BOControlTab


class BODurationTests(unittest.TestCase):
    def launch(self, duration, validation=False, fail=False):
        ga_duration = Mock()
        ga_duration.value.return_value = 17.0
        p = SimpleNamespace(
            _ga_auto_active=False, _pid_running=False,
            arm_output_check=Mock(), auto_ga_arm_check=Mock(),
            ga_evaluation_spin=ga_duration, ga_tuner=None,
            ga_status_label=Mock())
        p.arm_output_check.isChecked.return_value = True
        observed = []

        def start():
            observed.append(p._automatic_evaluation_duration_s)
            if fail:
                raise RuntimeError('launch failed')
            p._ga_auto_active = True
            p.ga_tuner = object()

        p._start_automatic_ga = start
        view = SimpleNamespace(
            pid_tab=p, arm=Mock(), status=Mock(), best=None,
            trial_duration=Mock(), _fingerprint=lambda: ('settings',))
        view.arm.isChecked.return_value = True
        view.trial_duration.value.return_value = duration
        with patch('importlib.util.find_spec', return_value=object()):
            if fail:
                with self.assertRaises(RuntimeError):
                    BOControlTab._launch(view, validation)
            else:
                BOControlTab._launch(view, validation)
        ga_duration.setValue.assert_not_called()
        self.assertFalse(hasattr(p, '_automatic_evaluation_duration_s'))
        self.assertFalse(hasattr(p, '_automatic_tuner_factory'))
        return observed[0]

    def test_search_uses_bo_duration(self):
        self.assertEqual(self.launch(42.5), 42.5)

    def test_validation_minimum(self):
        self.assertEqual(self.launch(12.0, validation=True), 60.0)

    def test_validation_preserves_longer_duration(self):
        self.assertEqual(self.launch(90.0, validation=True), 90.0)

    def test_failed_launch_cleans_up_override(self):
        self.assertEqual(self.launch(25.0, fail=True), 25.0)


if __name__ == '__main__':
    unittest.main()
