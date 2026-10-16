"""Native CST beam/RF plots and logarithmic histories embedded in TP gauges."""
from collections import deque
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QSizePolicy
from python.app.widgets.CstTrendWidget import CstTrendWidget


class CstVacuumWidget(CstTrendWidget):
    def __init__(self,parent=None,max_points=240,ymin=0.,ymax=100.,line=None,title="",embedded=False):
        super().__init__(parent,actual_color=line or "#78F0FF")
        self.max_points=int(max_points)
        self._buf=deque(maxlen=self.max_points)
        self._ymin,self._ymax=float(ymin),float(ymax)
        self.title=title
        self.embedded=embedded
        self.history_seconds=60.
        self._pulse_phase=0.
        self.setMinimumSize(1,1) if embedded else self.setMinimumSize(220,170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._animation_timer=QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        if not embedded:
            self._animation_timer.start(50)

    def _animate(self):
        self._pulse_phase+=.05
        self.update()

    def add_point(self,value):
        self._buf.append(float(value))
        self.update()

    def set_range(self,minimum,maximum):
        self._ymin,self._ymax=float(minimum),float(maximum)
        self.update()

    def set_history(self,values,color,seconds):
        import CombinationCharts as native
        self._native.actual_color=native.Color(color.redF(),color.greenF(),color.blueF())
        self._native.set_vacuum_data(list(values))
        self.history_seconds=float(seconds)
        self.update()

    def _render_chart(self):
        if not self.embedded:
            self._native.set_vacuum_data(list(self._buf))
        self._native.chart_title=self.title
        self._native.render_vacuum(self.width(),self.height(),self.devicePixelRatioF(),self.embedded,
                                   self._ymin,self._ymax,self.max_points,self._pulse_phase,self.history_seconds)
