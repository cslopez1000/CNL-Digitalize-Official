"""CST curve preview with native axes, nodes, glow and dashed reference."""
from python.app.widgets.CstTrendWidget import CstTrendWidget


class CstCalibrationWidget(CstTrendWidget):
    def __init__(self,parent=None):
        super().__init__(parent,x_axis_label="raw",y_axis_label="eng",
                         target_color="#FF4FD8",actual_color="#19F0FF",
                         relative_time=False,rolling_window_s=0,max_display_points=1000000)

    def set_curve(self,title,points,inverse=False):
        self._native.chart_title = title
        self._native.model.x_label = "eng" if inverse else "raw"
        self._native.model.y_label = "raw" if inverse else "eng"
        points = sorted(points)
        x,y = zip(*points) if len(points)>=2 else ([],[])
        self.set_data(x,y,y)

    def _render_chart(self):
        self._native.render_calibration(self.width(),self.height(),self.devicePixelRatioF())
