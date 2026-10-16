"""CST embedded beam-plot API with all graph drawing in C++."""
from collections import deque
import math
import time
from .CstTrendWidget import CstTrendWidget


class CstBeamWidget(CstTrendWidget):
    def __init__(self, parent=None):
        super().__init__(parent, rolling_window_s=0, relative_time=False, max_display_points=1800)
        self.samples = deque(maxlen=1800)
        self.setMinimumHeight(126)

    def append(self, value, stamp):
        if math.isfinite(value) and math.isfinite(stamp):
            self.samples.append((stamp, value))
            x, values = zip(*self.samples)
            self._native.model.set_data(x, values, values)
            self.update()

    def clear(self):
        self.samples.clear()
        super().clear()

    def _render_chart(self):
        self._native.render_beam(self.width(), self.height(), self.devicePixelRatioF(), time.monotonic())
