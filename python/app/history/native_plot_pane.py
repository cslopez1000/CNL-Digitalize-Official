"""CST plot-pane contract backed by native bounds, interaction mapping and GL.

The toolbar is extracted from CST. The small axis adapter preserves the viewer's
existing synchronized-range calls; it does not create Matplotlib axes/canvases.
"""
import math
from types import SimpleNamespace
import numpy as np
import pandas as pd
from PySide6 import QtCore, QtGui, QtWidgets
import CombinationCharts as native
from python.app.widgets.CstTrendWidget import CstTrendWidget


def native_color(value):
    color=QtGui.QColor(value)
    return native.Color(color.redF(),color.greenF(),color.blueF())


class HistoryCanvas(CstTrendWidget):
    dropped=QtCore.Signal(list)

    def __init__(self,pane):
        super().__init__(pane)
        self.pane=pane
        self._canvas=self
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Expanding)

    def draw_idle(self):
        self.update()

    def dragEnterEvent(self,event):
        event.acceptProposedAction() if event.mimeData().hasText() else event.ignore()

    dragMoveEvent=dragEnterEvent

    def dropEvent(self,event):
        if event.mimeData().hasText():
            names=[name.strip() for name in event.mimeData().text().splitlines() if name.strip()]
            self.dropped.emit(names)
            event.acceptProposedAction()

    def _point(self,event):
        position=event.position()
        return self._native.history_point(position.x(),position.y(),self.width(),self.height())

    def mouseMoveEvent(self,event):
        x,y=self._point(event)
        self._native.cursor_x=x
        self._native.cursor_y=y
        viewer=self.pane.viewer()
        self._native.cursor_text=(f"{viewer._format_marker_time(x)}\nValue: {y:.6g} {self.pane._display_unit}"
                                  if viewer and math.isfinite(x) else "")
        if viewer and math.isfinite(x): viewer._update_crosshair(x,self.pane)
        self.update()

    def leaveEvent(self,event):
        self._native.cursor_x=self._native.cursor_y=math.nan
        self._native.cursor_text=""
        self.update()

    def mousePressEvent(self,event):
        x,_=self._point(event)
        viewer=self.pane.viewer()
        if viewer and math.isfinite(x) and event.button()==QtCore.Qt.MouseButton.LeftButton:
            viewer._add_marker(x) if viewer.marker_mode_active else viewer._sync_crosshair_click(x)

    def wheelEvent(self,event):
        _,y=self._point(event)
        self.pane._zoom_y_axis(1.2 if event.angleDelta().y()>0 else 1/1.2,center=y)
        event.accept()

    def _render_chart(self):
        self._native.render_history(self.width(),self.height(),self.devicePixelRatioF())


class _Callbacks:
    def __init__(self,axis):
        self.axis=axis
        self.handlers=[]

    def connect(self,name,handler):
        if name=="xlim_changed": self.handlers.append(handler)

    def emit(self):
        for handler in self.handlers: handler(self.axis)


class _Axis:
    """Compatibility boundary for CST viewer range synchronization and reports."""
    def __init__(self,pane):
        self.pane=pane
        self.callbacks=_Callbacks(self)
        self.figure=SimpleNamespace(canvas=pane.canvas)

    def get_xlim(self): return tuple(self.pane.canvas._native.history_bounds()[:2])
    def get_ylim(self): return tuple(self.pane.canvas._native.history_bounds()[2:])
    def get_ylabel(self): return self.pane.canvas._native.history_label
    def get_yscale(self): return self.pane._y_axis_scale

    def set_xlim(self,limits):
        if tuple(limits)!=self.get_xlim():
            self.pane.canvas._native.history_x=list(limits)
            self.callbacks.emit()
        self.pane.canvas.update()

    def set_ylim(self,limits):
        self.pane.canvas._native.history_y=list(limits)
        self.pane.canvas.update()


class PlotPane(QtWidgets.QFrame):
    changed=QtCore.Signal()

    def __init__(self,title):
        super().__init__()
        from python.app.history.plot_controls import build_controls
        head=build_controls(self,title)
        self.canvas=HistoryCanvas(self)
        self.ax=_Axis(self)
        self.marker_lines=[]
        layout=QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12,9,12,8)
        layout.setSpacing(3)
        layout.addLayout(head)
        layout.addWidget(self.canvas,1)
        self.canvas.dropped.connect(self._apply_drop)

    def viewer(self):
        parent=self.parent()
        while parent and not hasattr(parent,"_display_series"): parent=parent.parent()
        return parent

    def _apply_drop(self,names):
        for name in names:
            if name not in self.series: self.series.append(name)
        self.changed.emit()
        viewer=self.viewer()
        if viewer: viewer.run_query()

    def _zoom_y_axis(self,factor,center=None):
        self.canvas._native.zoom_history(factor,math.nan if center is None else center)
        self.canvas.update()

    def _reset_zoom(self):
        self.canvas._native.history_y=[math.nan,math.nan]
        self.canvas.update()

    def _toggle_log_scale(self):
        self._y_axis_scale="log" if self.log_scale_btn.isChecked() else "linear"
        self.canvas._native.history_log=self._y_axis_scale=="log"
        self._reset_zoom()

    def _toggle_scientific_notation(self):
        self._use_scientific_notation=self.sci_notation_btn.isChecked()
        self.canvas._native.history_scientific=self._use_scientific_notation
        self.canvas.update()

    def _update_yaxis_formatter(self):
        self.canvas.update()

    def _resolve_series_name(self,name,df):
        from python.app.history.sqlite_viewer_qt import _resolve_series_name
        return _resolve_series_name(self,name,df)

    def clear_series(self):
        self.series.clear()
        self._trace_snapshots.clear()
        self._plot_warnings.clear()
        self.clear_markers()
        self.canvas._native.clear_monitor_series()
        self.canvas.update()
        self.changed.emit()

    def plot(self,times_num,df,preserve_markers=False):
        from python.app.history.sqlite_viewer_qt import NEON_COLORS,display_channel_labels,TraceSnapshot
        markers=list(self._marker_specs) if preserve_markers else []
        self._marker_specs=[]
        self._trace_snapshots=[]
        self._plot_warnings=[]
        plot=self.canvas._native
        plot.clear_monitor_series()
        plot.history_x=plot.history_y=[math.nan,math.nan]
        plot.history_label=""
        self._display_unit=""
        viewer=self.viewer()
        units,kinds=set(),set()
        if df is not None and not df.empty:
            for index,name in enumerate(self.series):
                column=self._resolve_series_name(name,df)
                if column:
                    display=viewer._display_series(name,column,df) if viewer else None
                    y=np.asarray(display.values if display else pd.to_numeric(df[column],errors="coerce"),dtype=float)
                    label,unit,kind=(display.label,display.unit,display.kind) if display else (display_channel_labels(name),"","recorded")
                    warning=display.warning if display else ""
                else:
                    y=np.full(len(times_num),np.nan)
                    label,unit,kind,warning=display_channel_labels(name),"","recorded","No numeric data"
                x=np.asarray(times_num,dtype=float)
                count=min(len(x),len(y))
                color=NEON_COLORS[index%len(NEON_COLORS)]
                snapshot=TraceSnapshot(name,label,unit,x[:count].copy(),y[:count].copy(),color,warning)
                self._trace_snapshots.append(snapshot)
                plot.set_monitor_series(index,snapshot.x.tolist(),snapshot.y.tolist(),native_color(color),label)
                units.add(unit);kinds.add(kind)
                if warning: self._plot_warnings.append(f"{display_channel_labels(name)}: {warning}")
        if viewer and viewer._scaling_enabled:
            if len(units)==1 and "" not in units:
                self._display_unit=next(iter(units))
                plot.history_label=f"Value [{self._display_unit}]"
            elif len(units)>1: plot.history_label="Value (units in legend)"
            else: plot.history_label="Recorded value" if kinds=={"recorded"} else "Scaled value"
        self._initial_ylim=self.ax.get_ylim()
        for marker in markers: self.add_marker(marker.x,marker.marker_id,marker.color,time_text=marker.time_text)
        self._update_markers()
        self.canvas.update()

    def _update_markers(self):
        from python.app.history.sqlite_viewer_report import marker_text
        self.canvas._native.set_history_markers([m.x for m in self._marker_specs],
            [marker_text(m,self._trace_snapshots) for m in self._marker_specs],
            [native_color(m.color) for m in self._marker_specs])
        self.canvas.update()

    def publish_report_palette(self,paper=False):
        from python.app.history.sqlite_viewer_report import _PAPER
        for index,trace in enumerate(self._trace_snapshots):
            color=_PAPER["colors"][index%len(_PAPER["colors"])] if paper else trace.color
            self.canvas._native.set_monitor_series(index,trace.x.tolist(),trace.y.tolist(),native_color(color),trace.label)

    def add_marker(self,x,marker_id,color,label_override=None,time_text=None):
        from python.app.history.sqlite_viewer_report import MarkerSnapshot
        viewer=self.viewer()
        stamp=time_text or (viewer._format_marker_time(x) if viewer else f"Sample {x:g}")
        self._marker_specs.append(MarkerSnapshot(float(x),int(marker_id),color,stamp))
        self._update_markers()

    def clear_markers(self):
        self._marker_specs=[]
        self.marker_lines=[]
        self._update_markers()

    def update_crosshair(self,x):
        if x is not None:
            self.canvas._native.cursor_x=float(x)
            self.canvas.update()

    def report_snapshot(self):
        from python.app.history.sqlite_viewer_report import PlotSnapshot
        return PlotSnapshot(self.title_lbl.text(),list(self._trace_snapshots),list(self._marker_specs),
                            self.ax.get_xlim(),self.ax.get_ylim(),self.ax.get_ylabel(),self._y_axis_scale,
                            self._use_scientific_notation,list(self._plot_warnings))
