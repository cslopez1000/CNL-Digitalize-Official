"""Native port of CST controller_theme.TrendPlot, without PID tick styling."""
import sys
from .CstTrendWidget import CstTrendWidget


class CstManualWidget(CstTrendWidget):
    def __init__(self, parent=None, **options):
        super().__init__(parent, rolling_window_s=0, relative_time=False,
                         max_display_points=sys.maxsize, **options)
        self.setMinimumHeight(230)

    def _render_chart(self):
        self._native.render_manual(self.width(), self.height(), self.devicePixelRatioF())
