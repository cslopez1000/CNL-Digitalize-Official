"""Thin Qt host for CST transport history; geometry and drawing are native."""
from python.app.widgets.CstTrendWidget import CstTrendWidget
from PySide6.QtWidgets import QSizePolicy


class CstTransportWidget(CstTrendWidget):
    def __init__(self, title, color, seconds, parent=None):
        super().__init__(parent, actual_color=color)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)
        self._native.monitor_title = title
        self._native.monitor_seconds = float(seconds)

    def setData(self, x, y, **_kwargs):
        # Preserve NaNs as finite-connect gaps; do not invent missing samples.
        self._native.set_monitor_data([float(v) for v in x], [float(v) for v in y])
        self.update()

    def _render_chart(self):
        self._native.render_transport(self.width(), self.height(), self.devicePixelRatioF())


class NativeShadow:
    """The native renderer draws shadow and curve together in one frame."""
    def setData(self, *_args, **_kwargs):
        pass

    def clear(self):
        pass
