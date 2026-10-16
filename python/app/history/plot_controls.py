"""CST plot toolbar/layout, extracted without behavioral edits."""
from PySide6 import QtWidgets
from python.app.history.sqlite_viewer_qt import apply_shadow, NEON_TEXT, PLOT_TITLE_SIZE, ZOOM_FACTOR

def build_controls(self,title):
    self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    self.setObjectName("PlotCard")
    apply_shadow(self, blur=24, y_offset=6)
    self.series: List[str] = []
    self._zoom_stack = []
    self._initial_ylim = None
    self._y_axis_scale = 'linear'
    self._use_scientific_notation = False
    self._format_index_time = False
    self._display_unit = ''
    self._trace_snapshots = []
    self._plot_warnings = []
    self._marker_specs = []
    self._positioning_markers = False

    self.title_lbl = QtWidgets.QLabel(title)
    self.title_lbl.setStyleSheet(f"font-weight:600; color:{NEON_TEXT}; font-size: {PLOT_TITLE_SIZE}px;")

    # Zoom buttons
    zoom_layout = QtWidgets.QHBoxLayout()

    self.zoom_in_btn = QtWidgets.QPushButton("+")
    self.zoom_in_btn.setMaximumWidth(30)
    self.zoom_in_btn.setToolTip("Zoom in (Y-axis)")
    self.zoom_in_btn.clicked.connect(lambda: self._zoom_y_axis(ZOOM_FACTOR))

    self.zoom_out_btn = QtWidgets.QPushButton("-")
    self.zoom_out_btn.setMaximumWidth(30)
    self.zoom_out_btn.setToolTip("Zoom out (Y-axis)")
    self.zoom_out_btn.clicked.connect(lambda: self._zoom_y_axis(1/ZOOM_FACTOR))

    self.reset_zoom_btn = QtWidgets.QPushButton("⟲")
    self.reset_zoom_btn.setMaximumWidth(30)
    self.reset_zoom_btn.setToolTip("Reset zoom")
    self.reset_zoom_btn.clicked.connect(self._reset_zoom)

    self.log_scale_btn = QtWidgets.QPushButton("Log")
    self.log_scale_btn.setMaximumWidth(40)
    self.log_scale_btn.setCheckable(True)
    self.log_scale_btn.setToolTip("Toggle logarithmic Y scale")
    self.log_scale_btn.clicked.connect(self._toggle_log_scale)

    self.sci_notation_btn = QtWidgets.QPushButton("Sci")
    self.sci_notation_btn.setMaximumWidth(40)
    self.sci_notation_btn.setCheckable(True)
    self.sci_notation_btn.setToolTip("Toggle scientific notation")
    self.sci_notation_btn.clicked.connect(self._toggle_scientific_notation)

    zoom_layout.addWidget(self.zoom_in_btn)
    zoom_layout.addWidget(self.zoom_out_btn)
    zoom_layout.addWidget(self.reset_zoom_btn)
    zoom_layout.addWidget(self.log_scale_btn)
    zoom_layout.addWidget(self.sci_notation_btn)
    zoom_layout.addStretch()

    clear = QtWidgets.QPushButton("Clear")
    clear.clicked.connect(self.clear_series)
    clear.setMaximumWidth(64)
    for button in (self.zoom_in_btn, self.zoom_out_btn, self.reset_zoom_btn,
                   self.log_scale_btn, self.sci_notation_btn, clear):
        button.setObjectName("PlotTool")
        button.setMinimumHeight(24)
    self.zoom_in_btn.setFixedWidth(30)
    self.zoom_out_btn.setFixedWidth(30)
    self.reset_zoom_btn.setFixedWidth(30)
    self.log_scale_btn.setFixedWidth(40)
    self.sci_notation_btn.setFixedWidth(40)
    zoom_layout.setSpacing(5)

    head = QtWidgets.QHBoxLayout()
    head.addWidget(self.title_lbl)
    head.addStretch()
    head.addLayout(zoom_layout)
    head.addWidget(clear)

    return head
