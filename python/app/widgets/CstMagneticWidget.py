"""CST grouped histories, overview bars and metric sparklines: C++ rendering."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QSizePolicy
import CombinationCharts as native
from python.app.widgets.CstTrendWidget import CstTrendWidget


class NativeSeries:
    def __init__(self, plot, index, color, name):
        self.plot, self.index, self.color, self.name = plot, index, QColor(color), name

    def setData(self, x, y=None):
        if y is None:
            y = list(x)
            x = range(len(y))
        c = self.color
        self.plot._native.set_monitor_series(self.index, list(x), list(y),
                                             native.Color(c.redF(),c.greenF(),c.blueF()),self.name)
        self.plot.update()

    def clear(self):
        self.setData([],[])


class NativeBar(NativeSeries):
    def setOpts(self, *, height):
        self.setData([self.index+1],height)


class CstMagneticWidget(CstTrendWidget):
    def __init__(self, title="", kind=0, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self._count = 0
        self.setMinimumHeight(0 if kind==1 else 100)
        self._native.monitor_title = title

    def add_series(self, color, name=""):
        series = (NativeBar if self.kind==2 else NativeSeries)(self,self._count,color,name)
        self._count += 1
        series.clear()
        return series

    def _render_chart(self):
        self._native.render_magnetic(self.width(),self.height(),self.devicePixelRatioF(),self.kind)

    def setXRange(self, minimum, maximum, **_kwargs):
        """CST source plots call this after setting latest-relative coordinates."""
        if self.kind != 3 or maximum != 0 or minimum >= 0:
            raise ValueError("Source history must end at zero and start at a negative age")
        self._native.monitor_seconds = -float(minimum)
        self.update()
