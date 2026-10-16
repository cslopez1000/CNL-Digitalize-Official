"""CST PIDGainRadar API; normalization, scales and rendering execute in C++."""
from .CstTrendWidget import CstTrendWidget


class CstGainWidget(CstTrendWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(170,170)

    def set_gains(self, kp, ki, kd):
        self._native.gains = [float(kp),float(ki),float(kd)]
        self.update()

    def _render_chart(self):
        self._native.render_gains(self.width(), self.height(), self.devicePixelRatioF())
