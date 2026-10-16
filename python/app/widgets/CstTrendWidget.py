"""CST trend API; C++ owns preparation, axes, geometry and OpenGL drawing."""
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QOpenGLContext, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from shiboken6 import getCppPointer
import CombinationCharts as native


class CstTrendWidget(QOpenGLWidget):
    render_failed = Signal(str)

    def __init__(self, parent=None, y_axis_label="CURRENT (A)", x_axis_label="TIME (s)",
                 target_color="#69BDF7", actual_color="#F49A28", third_color="#62E873",
                 x_tick_count=6, y_tick_count=5, rolling_window_s=None,
                 relative_time=None, max_display_points=600, allow_missing_target=False):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(4, 6)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setSamples(4)
        self.setFormat(fmt)
        self.setMinimumHeight(140)
        self._native = native.CstTrendPlot()
        model = self._native.model
        model.x_label, model.y_label = str(x_axis_label), str(y_axis_label)
        is_time = "TIME" in model.x_label.upper()
        model.rolling_window = max(0.0, float(120 if is_time else 0) if rolling_window_s is None else float(rolling_window_s))
        model.relative_time = is_time if relative_time is None else bool(relative_time and is_time)
        model.max_points = max(50, int(max_display_points))
        model.allow_missing_target = bool(allow_missing_target)
        model.x_ticks, model.y_ticks = max(3, int(x_tick_count)), max(3, int(y_tick_count))
        for key, value in (("target_color", target_color), ("actual_color", actual_color), ("third_color", third_color or "#62E873")):
            color = QColor(value)
            setattr(self._native, key, native.Color(color.redF(), color.greenF(), color.blueF()))
        self.error = ""
        self._ready = False

    def set_data(self, x_data, target_data, actual_data, third_data=None):
        # Preserve CST coercion semantics for nonnumeric rows; all numeric
        # filtering, windowing, decimation and axes then execute in C++.
        import math
        columns = [x_data, target_data, actual_data]
        if third_data is not None:
            columns.append(third_data)
        rows = []
        for row in zip(*columns):
            try:
                values = tuple(float(v) for v in row)
            except (TypeError, ValueError):
                continue
            required = values[:1] + values[2:] if self._native.model.allow_missing_target else values
            if all(math.isfinite(v) for v in required):
                rows.append(values)
        data = list(zip(*rows)) if rows else [()] * len(columns)
        self._native.model.set_data(*data)
        self.update()

    def clear(self):
        self._native.model.set_data([], [], [])
        self.update()

    @property
    def y_axis_label(self):
        return self._native.model.y_label

    @y_axis_label.setter
    def y_axis_label(self, value):
        self._native.model.y_label = str(value)
        self.update()

    def _activate(self):
        context = QOpenGLContext.currentContext()
        if context is None or context != self.context():
            raise RuntimeError("The graph's own context must be current")
        native.set_current_render_context(getCppPointer(context)[0])

    def initializeGL(self):
        try:
            self._activate()
            context = self.context()
            native.load_opengl(lambda name: int(context.getProcAddress(name.encode("ascii")) or 0))
            context.aboutToBeDestroyed.connect(self.release_native_resources)
            self._ready = True
            self.error = ""
        except Exception as exc:
            self.error = str(exc)
            self.render_failed.emit(self.error)

    def paintGL(self):
        if not self._ready:
            return
        try:
            self._activate()
            self._render_chart()
        except Exception as exc:
            self.error = str(exc)
            self._ready = False
            self.render_failed.emit(self.error)
        finally:
            native.set_current_render_context(0)

    def _render_chart(self):
        self._native.render(self.width(), self.height(), self.devicePixelRatioF())

    def release_native_resources(self):
        context = self.context()
        if context is None or not context.isValid():
            return
        self.makeCurrent()
        try:
            self._activate()
            self._native.release_resources()
        finally:
            native.set_current_render_context(0)
            self.doneCurrent()

    def closeEvent(self, event):
        self.release_native_resources()
        super().closeEvent(event)
