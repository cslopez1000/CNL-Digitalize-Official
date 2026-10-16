# sqlite_viewer_qt.py — CNL record viewer, Tesla-inspired dark interface.
# Based on the uploaded viewer. SQLite queries, schema, alias resolution,
# time-window selection, and sample-index plotting are retained.
# Keep cnl_logo.png and sqlite_viewer_scaling.py beside this file.
# Scaling factors ON/OFF changes the display only; raw SQLite rows stay unchanged.
# Trimming-coil labels use TC1–TC12; database/calibration/drag keys remain ch1–ch12.
# Calibration files are read, never replaced. No sqlite_logger.py changes are required.
# Marker values and PDF export also require sqlite_viewer_report.py beside this file.
# -*- coding: utf-8 -*-

# --- must be the very first matplotlib lines ---
import matplotlib
matplotlib.use("QtAgg")  # Qt canvas compatible with this application's PySide6 widgets

import sys, os, sqlite3
import re
from functools import lru_cache, partial
from typing import List
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from python.app.history.sqlite_viewer_scaling import ViewerCalibration, identify_column, related_columns
from python.app.history.sqlite_viewer_report import (
    TraceSnapshot, MarkerSnapshot, PlotSnapshot, ReportInfo, snap_sample,
    marker_text, add_marker_artists, position_marker_labels, export_pdf,
)

from PySide6 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.ticker import NullFormatter, MaxNLocator, ScalarFormatter

# ---------------- Config ----------------
LV_OFFSET = 2082844800.0  # LabVIEW -> Unix offset (sec)
DEFAULT_DB = os.environ.get("CNL_SQLITE", "cyclotron_data_fresh.db")
DEBUG = os.environ.get("VIEWER_DEBUG", "0") == "1"

# ---- FIXED CONFIGURABLE PARAMETERS ----
AXIS_LABEL_SIZE = 10
AXIS_TICK_SIZE  = 9
LEGEND_FONT_SIZE= 9
PLOT_TITLE_SIZE = 12
UI_FONT_SIZE    = 11
STATUS_FONT_SIZE= 10

# Layout proportions
COLUMNS_PANEL_WIDTH = 20
PLOTS_PANEL_WIDTH   = 80

# Point limiting
DEFAULT_MAX_POINTS  = 500

# Window dimensions
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MIN_WIDTH = 1000
MIN_HEIGHT = 700

# Zoom parameters
ZOOM_FACTOR = 1.2
MIN_Y_RANGE = 1e-10

# ---- Viewer-local Tesla-inspired theme ----
# Existing NEON_* names are kept so the plotting code does not need rewiring.
NEON_BG     = "#090A0C"
NEON_PANEL  = "#181A1E"
NEON_GRID   = "#30343B"
NEON_SPINE  = "#424852"
NEON_TEXT   = "#ECEFF3"
NEON_DIM    = "#A4ADB9"
ACCENT      = "#E83B45"
NEON_COLORS = ["#ED4A54", "#D8DEE8", "#82A9CF", "#C2AC80", "#81B5A8", "#BBA1C9"]
MARKER_COLORS = ["#ED4A54", "#D8DEE8", "#82A9CF", "#C2AC80", "#81B5A8", "#BBA1C9"]

APP_TITLE = "CNL | Record Viewer"
from python.application.paths import ROOT
SCRIPT_DIR = str(ROOT / "assets/ui")

# Match complete ch1–ch12 identifiers, optionally followed by a suffix such
# as _raw / _eu. Do not match ch13, ch100, or names containing an embedded ch1.
_TRIM_LABEL_PATTERN = re.compile(r"\bch(1[0-2]|[1-9])(?=\b|_)")


def display_channel_labels(text: str) -> str:
    """Format visible text only; never use this output as a database key.

    Keep suffixes/units visible so stored and raw variants remain distinct.
    main_magnet, centering_beam, and all other variable names stay unchanged.
    """
    return _TRIM_LABEL_PATTERN.sub(r"TC\1", text)


def load_logo_pixmap(size=76):
    """Load the user's logo from a portable path; no hard-coded machine paths."""
    candidates = (
        os.environ.get("CNL_VIEWER_LOGO", ""),
        os.path.join(SCRIPT_DIR, "cnl_logo.png"),
        os.path.join(SCRIPT_DIR, "assets", "cnl_logo.png"),
    )
    for path in candidates:
        if path and os.path.isfile(path):
            pixmap = QtGui.QPixmap(path)
            if not pixmap.isNull():
                # Retain extra pixels for high-DPI Windows displays.
                result = pixmap.scaled(
                    size * 2, size * 2,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                result.setDevicePixelRatio(2.0)
                return result
    return None


def apply_shadow(widget, blur=28, y_offset=7):
    effect = QtWidgets.QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QtGui.QColor(0, 0, 0, 180))
    widget.setGraphicsEffect(effect)


def viewer_stylesheet():
    """Scoped to this widget, not QApplication or the rest of the controller."""
    return f"""
        QWidget {{
            color: {NEON_TEXT};
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: {UI_FONT_SIZE}px;
        }}
        QWidget#CNLRecordViewer {{ background-color: {NEON_BG}; }}
        QFrame#HeaderCard, QFrame#ControlCard, QFrame#SideCard, QFrame#PlotCard {{
            background-color: {NEON_PANEL};
            border: 1px solid #343941;
            border-radius: 14px;
        }}
        QFrame#HeaderCard {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1D2025, stop:1 #131518);
        }}
        QLabel {{ background: transparent; border: none; }}
        QLabel#AppTitle {{ font-size: 23px; font-weight: 600; }}
        QLabel#AppSubtitle {{ color: {NEON_DIM}; font-size: 11px; }}
        QLabel#SectionLabel {{ color: {NEON_DIM}; font-size: 10px; font-weight: 600; }}
        QLabel#ViewerBadge {{
            color: #F1B6BA; background: #342126;
            border: 1px solid #663138; border-radius: 11px;
            padding: 5px 13px; font-size: 10px; font-weight: 600;
        }}
        QLabel#StatusLabel {{
            color: {NEON_DIM}; background: #111317;
            border: 1px solid #282D34; border-radius: 9px;
            padding: 7px 11px;
        }}
        QListWidget {{
            background: #121418; border: 1px solid #30353D;
            border-radius: 10px; padding: 5px; outline: none;
            color: {NEON_TEXT}; font-size: 12px;
        }}
        QListWidget::item {{
            padding: 7px 8px; margin: 1px 0px;
            border: 1px solid transparent; border-radius: 6px;
        }}
        QListWidget::item:hover {{ background: #242830; }}
        QListWidget::item:selected {{
            color: #FFFFFF; background: #3A242B; border: 1px solid #87414B;
        }}
        QPushButton {{
            background: #272B32; color: {NEON_TEXT};
            border: 1px solid #3E444E; border-radius: 9px;
            padding: 6px 11px; min-height: 19px; font-weight: 500;
        }}
        QPushButton:hover {{ background: #333943; border-color: #646D7C; }}
        QPushButton:pressed {{ background: #1E2228; }}
        QPushButton:focus {{ border-color: {ACCENT}; }}
        QPushButton:checked {{ background: #46282E; border-color: {ACCENT}; }}
        QPushButton:disabled {{ color: #727985; background: #1A1D22; }}
        QPushButton#PrimaryButton {{
            background: {ACCENT}; border-color: {ACCENT}; color: white;
        }}
        QPushButton#PrimaryButton:hover {{ background: #F24D57; border-color: #F24D57; }}
        QPushButton#PrimaryButton:pressed {{ background: #C42C38; }}
        QPushButton#PlotTool {{ padding: 2px 5px; min-height: 20px; border-radius: 7px; }}
        QLineEdit, QDateTimeEdit, QSpinBox {{
            background: #101216; color: {NEON_TEXT};
            border: 1px solid #3D444E; border-radius: 8px;
            padding: 6px 9px; min-height: 20px;
            selection-background-color: #66333D;
        }}
        QLineEdit:focus, QDateTimeEdit:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
        QCalendarWidget QWidget {{ background: #191C21; color: {NEON_TEXT}; }}
        QCalendarWidget QAbstractItemView {{
            background: #191C21; color: {NEON_TEXT};
            selection-background-color: #71343F;
        }}
        QScrollBar:vertical {{ background: #13161A; width: 10px; margin: 3px 1px; }}
        QScrollBar::handle:vertical {{ background: #454D59; min-height: 25px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: #687483; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        QScrollBar:horizontal {{ background: #13161A; height: 10px; margin: 1px 3px; }}
        QScrollBar::handle:horizontal {{ background: #454D59; min-width: 25px; border-radius: 4px; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        QMenu {{ background: #181A1E; color: {NEON_TEXT}; border: 1px solid #424852; padding: 5px; }}
        QMenu::item {{ padding: 7px 15px; border-radius: 5px; }}
        QMenu::item:selected {{ background: #46282E; }}
        QMenu::separator {{ height: 1px; background: #424852; margin: 4px 8px; }}
        QDialog#ExportDialog {{ background: #181A1E; }}
        QCheckBox {{ color: {NEON_TEXT}; spacing: 8px; min-height: 22px; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; }}
        QMessageBox {{ background: #181A1E; }}
        QMessageBox QTextEdit {{ background: #101216; color: {NEON_TEXT}; }}
        QToolTip {{ color: #ECEFF3; background: #252A32; border: 1px solid #596270; padding: 5px; }}
    """


def neonize_axes(ax):
    ax.set_facecolor(NEON_PANEL)
    ax.tick_params(colors=NEON_TEXT, labelsize=AXIS_TICK_SIZE)
    ax.xaxis.label.set_color(NEON_TEXT)
    ax.yaxis.label.set_color(NEON_TEXT)
    ax.xaxis.label.set_size(AXIS_LABEL_SIZE)
    ax.yaxis.label.set_size(AXIS_LABEL_SIZE)
    for s in ax.spines.values():
        s.set_color(NEON_SPINE); s.set_linewidth(0.8)
    ax.grid(True, color=NEON_GRID, alpha=0.6, linewidth=0.6)
    ax.set_axisbelow(True)

def glow_line(ax, x, y, color, label=None):
    # Restrained trace styling instead of the original multi-layer neon glow.
    ax.plot(x, y, color=color, linewidth=1.5, label=label)
    ax.scatter(x, y, s=5, color=color, edgecolors="none", alpha=0.55, zorder=3)

# ------------ Drag source (columns) ------------
class ColumnList(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QListWidget.SelectionMode.ExtendedSelection)
        self._drag_start = None

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self._drag_start = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if not (e.buttons() & QtCore.Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(e)
        if (self._drag_start is None or
            (e.pos() - self._drag_start).manhattanLength() < QtWidgets.QApplication.startDragDistance()):
            return
        items = self.selectedItems()
        if not items:
            item = self.itemAt(self._drag_start)
            if item: items = [item]
        if not items:
            return
        mime_data = QtCore.QMimeData()
        # Display labels can differ from the real SQLite column names.
        # Drag the stored keys, not the visible TC labels, so both SELECTs
        # and calibration lookup still receive ch1, ch2, ... unchanged.
        mime_data.setText("\n".join(
            it.data(QtCore.Qt.ItemDataRole.UserRole) or it.text() for it in items))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(QtCore.Qt.DropAction.CopyAction)

# ------------ QWidget wrapper around the MPL canvas ------------
def _resolve_series_name(self, name: str, df: pd.DataFrame) -> str | None:
    legacy_map = {
        "inside_iron": "inside_iron_a",
        "inside_iron_raw": "inside_iron_a_raw",
        "inside_iron_eu": "inside_iron_a_eu",
        "outside_iron": "outside_iron_a",
        "outside_iron_raw": "outside_iron_a_raw",
        "outside_iron_eu": "outside_iron_a_eu",
    }
    if name in legacy_map:
        name = legacy_map[name]

    def has_data(col):
        return (col in df.columns) and pd.to_numeric(df[col], errors="coerce").notna().any()

    if has_data(name):
        return name

    cands = []
    if name.endswith("_raw"):
        base = name[:-4]; cands += [base + "_mbar", base + "_eu"]
    elif name.endswith("_mbar") or name.endswith("_eu"):
        base = name.rsplit("_", 1)[0]; cands += [base + "_raw"]
    else:
        cands += [name + "_mbar", name + "_eu", name + "_raw"]

    if name in ("beam_current", "beam"):
        cands = [name, "beam_ua", "beam_raw"] + cands
    if name in ("rf_kv", "rf"):
        cands = [name, "rf_power_kv", "rf_kv_raw"] + cands
    if name.startswith("vac") and len(name) > 3 and name[3].isdigit():
        base = name.split("_", 1)[0]
        cands = [base + "_mbar", base + "_raw", base] + cands
    if name in ("main_magnet", "centering_beam"):
        cands = [name + "_eu", name + "_raw", name] + cands

    for c in cands:
        if has_data(c):
            return c
    key = identify_column(name)[0]
    for c in sorted(related_columns(name)):
        if identify_column(c)[0] == key and has_data(c):
            return c
    return None

from python.app.history.native_plot_pane import PlotPane

# ---------------- Main viewer widget ----------------
class SQLiteLogViewer(QtWidgets.QWidget):
    def __init__(self, db_path: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("CNLRecordViewer")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(APP_TITLE)
        logo = load_logo_pixmap(96)
        if logo is not None:
            self.setWindowIcon(QtGui.QIcon(logo))
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self._db_path = db_path or DEFAULT_DB
        self._loaded_db_path = self._db_path
        self._loaded_epoch = "unix"  # Epoch belonging to the cached displayed rows.
        self._last_pdf_dir = os.path.expanduser('~')

        # Marker system
        self.marker_mode_active = False
        self.marker_counter = 0
        self.current_markers = []

        self._db_cols = set()  # populated by load_columns()
        self._scaling_enabled = False
        self._calibration = ViewerCalibration(SCRIPT_DIR)
        self._scaling_results = {}

        self.setStyleSheet(viewer_stylesheet())

        self._create_top_bar()
        self._create_main_layout()
        self._connect_signals()

        self._last_df = pd.DataFrame()
        self._last_df_shown = pd.DataFrame()
        self._format_time_as_index = False
        self._current_crosshair_x = None
        # Open the interface even when the default DB is not beside the script.
        if os.path.isfile(self._db_path):
            self.load_columns(autofit_window=True)
        else:
            self.status.setText("Open a SQLite database using Browse DB to begin.")

    def _create_top_bar(self):
        self.db_edit = QtWidgets.QLineEdit(self._db_path)
        self.db_edit.setMinimumWidth(160)
        self.db_edit.setToolTip("Path to your existing SQLite database")

        self.browse = QtWidgets.QPushButton("Browse DB")
        self.browse.setObjectName("PrimaryButton")
        self.reload_cols = QtWidgets.QPushButton("Reload Columns")
        self.jump_latest_btn = QtWidgets.QPushButton("Jump to Latest")
        self.check_b = QtWidgets.QPushButton("Check Window")

        self.points_n = QtWidgets.QSpinBox()
        self.points_n.setRange(10, 20000)
        self.points_n.setValue(DEFAULT_MAX_POINTS)
        self.points_n.setSuffix(" pts")
        self.points_n.setMaximumWidth(110)
        self.points_n.setToolTip("Maximum displayed points; recorded data is not changed")

        self.marker_btn = QtWidgets.QPushButton("Marker Mode")
        self.marker_btn.setCheckable(True)
        self.marker_btn.setToolTip(
            "Enable, then click a plot to mark the nearest displayed sample.\n"
            "Every plot shows its own signal values in the current display units.")
        self.clear_markers_btn = QtWidgets.QPushButton("Clear")
        self.clear_markers_btn.setToolTip("Remove all markers from all three plots")
        self.export_pdf_btn = QtWidgets.QPushButton("Export PDF…")
        self.export_pdf_btn.setToolTip("Save selected plots, current scaling and zoom, with optional markers")

        self.scaling_btn = QtWidgets.QPushButton("Scaling factors: OFF")
        self.scaling_btn.setCheckable(True)
        self.scaling_btn.setToolTip(
            "Switch every plot between recorded values and calibrated engineering units.\n"
            "Display only: the SQLite records are never changed.\n"
            "Right-click to choose calibration files, reload them, or view details.")
        self.scaling_btn.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.scaling_info = QtWidgets.QLabel("Recorded values · display only")
        self.scaling_info.setObjectName("AppSubtitle")
        self.scaling_info.setWordWrap(True)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(QtWidgets.QLabel("Database"))
        top.addWidget(self.db_edit, 1)
        top.addWidget(self.browse)
        top.addWidget(self.reload_cols)
        self.top_bar_layout = top

    def _create_main_layout(self):
        # Branded header: your logo, not a Tesla logo.
        header = QtWidgets.QFrame()
        header.setObjectName("HeaderCard")
        apply_shadow(header)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(18, 8, 18, 8)
        header_layout.setSpacing(16)

        self.logo_label = QtWidgets.QLabel()
        self.logo_label.setFixedSize(78, 72)
        self.logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        logo = load_logo_pixmap(72)
        if logo is not None:
            self.logo_label.setPixmap(logo)
        else:
            self.logo_label.setText("CNL")
            self.logo_label.setToolTip("Place cnl_logo.png beside this Python file")
        header_layout.addWidget(self.logo_label)

        titles = QtWidgets.QVBoxLayout()
        titles.setSpacing(3)
        title = QtWidgets.QLabel("Record Viewer")
        title.setObjectName("AppTitle")
        subtitle = QtWidgets.QLabel("CROCKER NUCLEAR LABORATORY  /  UC DAVIS")
        subtitle.setObjectName("AppSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header_layout.addLayout(titles, 1)
        badge = QtWidgets.QLabel("SQLITE RECORDS")
        badge.setObjectName("ViewerBadge")
        header_layout.addWidget(badge)
        self.brand_header = header

        self.col_list = ColumnList()
        self.col_list.setMinimumWidth(190)
        self.col_list.setToolTip("Select one or more columns and drag them onto a plot")

        self.start_dt = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime().addSecs(-300))
        self.start_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_dt.setCalendarPopup(True)
        self.start_dt.setMinimumWidth(182)
        self.start_dt.setMaximumWidth(215)
        self.end_dt = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        self.end_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_dt.setCalendarPopup(True)
        self.end_dt.setMinimumWidth(182)
        self.end_dt.setMaximumWidth(215)

        time_row = QtWidgets.QHBoxLayout()
        time_row.setSpacing(8)
        time_row.addWidget(QtWidgets.QLabel("From"))
        time_row.addWidget(self.start_dt)
        time_row.addSpacing(8)
        time_row.addWidget(QtWidgets.QLabel("To"))
        time_row.addWidget(self.end_dt)
        time_row.addStretch(1)
        time_row.addWidget(self.jump_latest_btn)

        controls = QtWidgets.QFrame()
        controls.setObjectName("ControlCard")
        apply_shadow(controls, blur=22, y_offset=5)
        controls_layout = QtWidgets.QVBoxLayout(controls)
        controls_layout.setContentsMargins(13, 11, 13, 11)
        controls_layout.setSpacing(9)
        controls_layout.addLayout(self.top_bar_layout)
        controls_layout.addLayout(time_row)

        self.p1, self.p2, self.p3 = PlotPane("Plot A"), PlotPane("Plot B"), PlotPane("Plot C")
        plots_layout = QtWidgets.QVBoxLayout()
        plots_layout.setSpacing(12)
        for pane in (self.p1, self.p2, self.p3):
            pane.canvas.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                      QtWidgets.QSizePolicy.Policy.Expanding)
            pane.setMinimumHeight(145)
            plots_layout.addWidget(pane, 1)

        self.status = QtWidgets.QLabel("Drag variables to plots | Click to sync crosshair | Wheel to zoom Y")
        self.status.setObjectName("StatusLabel")
        self.status.setWordWrap(True)

        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("SideCard")
        sidebar.setMinimumWidth(226)
        sidebar.setMaximumWidth(300)
        apply_shadow(sidebar)
        left = QtWidgets.QVBoxLayout(sidebar)
        left.setContentsMargins(13, 15, 13, 13)
        left.setSpacing(9)
        section = QtWidgets.QLabel("RECORDED VARIABLES")
        section.setObjectName("SectionLabel")
        left.addWidget(section)
        hint = QtWidgets.QLabel("Drag columns onto a plot")
        hint.setObjectName("AppSubtitle")
        left.addWidget(hint)
        left.addWidget(self.col_list, 1)
        left.addSpacing(5)
        tools_label = QtWidgets.QLabel("DISPLAY TOOLS")
        tools_label.setObjectName("SectionLabel")
        left.addWidget(tools_label)
        points_row = QtWidgets.QHBoxLayout()
        points_row.addWidget(QtWidgets.QLabel("Max points"))
        points_row.addStretch(1)
        points_row.addWidget(self.points_n)
        left.addLayout(points_row)
        left.addWidget(self.scaling_btn)
        left.addWidget(self.scaling_info)
        markers_row = QtWidgets.QHBoxLayout()
        markers_row.addWidget(self.marker_btn, 1)
        markers_row.addWidget(self.clear_markers_btn)
        left.addLayout(markers_row)
        left.addWidget(self.check_b)
        left.addWidget(self.export_pdf_btn)

        right = QtWidgets.QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(controls)
        right.addLayout(plots_layout, 1)
        right.addWidget(self.status)

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(14)
        content.addWidget(sidebar, COLUMNS_PANEL_WIDTH)
        content.addLayout(right, PLOTS_PANEL_WIDTH)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(14)
        root.addWidget(header)
        root.addLayout(content, 1)

    def _connect_signals(self):
        self.browse.clicked.connect(self._on_browse)
        self.reload_cols.clicked.connect(lambda: self.load_columns(autofit_window=False))
        self.jump_latest_btn.clicked.connect(lambda: self.jump_to_latest(300))
        self.check_b.clicked.connect(self._check_window)
        self.marker_btn.toggled.connect(self._on_marker_mode_toggled)
        self.clear_markers_btn.clicked.connect(self._clear_all_markers)
        self.export_pdf_btn.clicked.connect(self._export_pdf_dialog)
        self.scaling_btn.toggled.connect(self._on_scaling_toggled)
        self.scaling_btn.customContextMenuRequested.connect(self._scaling_menu)

        self.start_dt.dateTimeChanged.connect(self.run_query)
        self.end_dt.dateTimeChanged.connect(self.run_query)
        self.points_n.valueChanged.connect(self.run_query)

        for p in (self.p1, self.p2, self.p3):
            p.canvas.dropped.connect(partial(self._after_drop, pane=p))
            p.ax.callbacks.connect("xlim_changed", partial(self._sync_xlim_from, p.ax))

    # ---------- helpers ----------
    def _warn(self, title, msg):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def _connect(self):
        path = self.db_edit.text().strip()
        if not os.path.exists(path):
            self._warn("Database", f"Path not found:\n{path}")
            raise FileNotFoundError(path)
        return sqlite3.connect(path)

    def _detect_db_epoch(self) -> str:
        # NO caching: correct even when switching DBs
        try:
            with self._connect() as c:
                mn = c.execute("SELECT MIN(timestamp) FROM channel_data").fetchone()[0]
            return "labview" if (mn is not None and float(mn) > 3e9) else "unix"
        except Exception:
            return "unix"

    def _latest_timestamp(self) -> float | None:
        try:
            with self._connect() as c:
                mx = c.execute("SELECT MAX(timestamp) FROM channel_data").fetchone()[0]
            return float(mx) if mx is not None else None
        except Exception:
            return None

    def _time_clause(self) -> str:
        epoch = self._detect_db_epoch()
        s = self.start_dt.dateTime().toSecsSinceEpoch()
        e = self.end_dt.dateTime().toSecsSinceEpoch()
        if epoch == "labview":
            s += LV_OFFSET
            e += LV_OFFSET
        return f"FROM channel_data WHERE timestamp BETWEEN {s:.6f} AND {e:.6f}"

    def _decimate_uniform(self, df: pd.DataFrame, n: int) -> pd.DataFrame:
        if df is None or df.empty or len(df) <= n:
            return df
        idx = np.linspace(0, len(df) - 1, n, dtype=int)
        return df.iloc[idx].reset_index(drop=True)

    # ----------- key FIX: expand needed columns for fallbacks -----------
    def _expand_needed_cols(self, series_names: List[str]) -> List[str]:
        """
        Build a SELECT column list that includes the dragged names AND their likely aliases,
        so PlotPane._resolve_series_name() can actually find real data.
        """
        legacy_map = {
            "inside_iron": "inside_iron_a",
            "inside_iron_raw": "inside_iron_a_raw",
            "inside_iron_eu": "inside_iron_a_eu",
            "outside_iron": "outside_iron_a",
            "outside_iron_raw": "outside_iron_a_raw",
            "outside_iron_eu": "outside_iron_a_eu",
        }

        needed = {"timestamp"}

        for n in series_names:
            base = legacy_map.get(n, n)
            needed.add(base)

            # add common variants
            if base.endswith("_raw"):
                b = base[:-4]
                needed.add(b + "_eu")
                needed.add(b + "_mbar")
            elif base.endswith("_eu") or base.endswith("_mbar"):
                b = base.rsplit("_", 1)[0]
                needed.add(b + "_raw")
            else:
                needed.add(base + "_raw")
                needed.add(base + "_eu")
                needed.add(base + "_mbar")

            # special cases
            if n in ("beam_current", "beam"):
                needed |= {"beam_current", "beam_ua", "beam_raw"}
            if n in ("rf_kv", "rf"):
                needed |= {"rf_kv", "rf_power_kv", "rf_kv_raw"}

        for name in series_names:
            needed.update(related_columns(name))

        # keep only columns that exist to avoid SQL errors
        if self._db_cols:
            needed = {c for c in needed if c in self._db_cols}

        # stable order (timestamp first)
        out = ["timestamp"] + sorted([c for c in needed if c != "timestamp"])
        return out

    # ---------- viewer-only engineering-unit display ----------
    def _display_series(self, name, source, df):
        result = self._calibration.display(name, source, df, self._scaling_enabled)
        # Conversion uses the original keys; only the resulting legend is relabeled.
        result.label = display_channel_labels(result.label)
        self._scaling_results[name] = result
        return result

    def _on_scaling_toggled(self, checked):
        self._scaling_enabled = bool(checked)
        for pane in (self.p1, self.p2, self.p3):
            pane._zoom_stack.clear()  # Old Y limits belong to different units.
            pane._initial_ylim = None
        self._render_current_data(preserve_view=True)

    def _scaling_details(self):
        lines = [
            "DISPLAY ONLY — SQLite records and calibration files are not modified.",
            "OFF: show the stored values. ON: use raw_to_eng calibration / recorded beam range.",
            "Raw/base columns follow the supplied logger's raw-packet schema.",
            "Explicit *_eu / *_mbar / beam_*a engineering columns are not rescaled.",
            "Raw records use the currently loaded calibration, not a historical calibration version.",
            "Beam values use a constant nA display unit. Unknown ranges are omitted, not guessed.",
            "", "Calibration files:",
        ]
        for kind, title in (("channels", "Channels"), ("beam", "Beam")):
            lines.append(f"{title}: {self._calibration.paths.get(kind, 'not loaded')}")
            if kind in self._calibration.errors:
                lines.append(f"  {self._calibration.errors[kind]}")
        active = set(self.p1.series + self.p2.series + self.p3.series)
        for name, result in self._scaling_results.items():
            if name in active:
                # Keep the note's original SQLite/calibration key for traceability.
                lines.append(f"\n{display_channel_labels(name)}: {result.note or result.kind}")
                if result.warning:
                    lines.append(f"  WARNING: {display_channel_labels(result.warning)}")
        return "\n".join(lines)

    def _update_scaling_ui(self):
        self.scaling_btn.setText("Scaling factors: ON" if self._scaling_enabled else "Scaling factors: OFF")
        warnings = sum(bool(result.warning) for result in self._scaling_results.values())
        caption = "Engineering units · display only" if self._scaling_enabled else "Recorded values · display only"
        if self._scaling_enabled and warnings:
            caption += f"\n{warnings} conversion warning(s) — right-click for details"
        self.scaling_info.setText(caption)
        self.scaling_info.setToolTip(self._scaling_details())

    def _scaling_menu(self, position):
        menu = QtWidgets.QMenu(self)
        choose_channels = menu.addAction("Choose calibration.json…")
        choose_beam = menu.addAction("Choose beam_cal.json…")
        menu.addSeparator()
        reload_action = menu.addAction("Reload calibration files")
        details_action = menu.addAction("Show scaling details")
        action = menu.exec(self.scaling_btn.mapToGlobal(position))
        if action in (choose_channels, choose_beam):
            kind = "channels" if action is choose_channels else "beam"
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Select existing calibration file",
                self._calibration.paths.get(kind, SCRIPT_DIR), "Calibration (*.json);;All files (*)")
            if path:
                self._calibration.overrides[kind] = path
                self._render_current_data(preserve_view=True)
        elif action is reload_action:
            self._render_current_data(preserve_view=True)
        elif action is details_action:
            self._calibration.refresh(self.db_edit.text().strip())
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("Scaling factors — display only")
            box.setText("Each channel uses its calibration. Beam samples use their recorded range.")
            box.setInformativeText("Open Details to see the loaded files and any conversion warnings.")
            box.setDetailedText(self._scaling_details())
            box.exec()

    def _render_current_data(self, preserve_view=False):
        self._calibration.refresh(self.db_edit.text().strip())
        self._scaling_results = {}
        df = self._last_df_shown
        panes = (self.p1, self.p2, self.p3)
        if not preserve_view:
            # A new query / decimation has new sample indices. Never attach an
            # old marker to a different timestamp. Unit toggles do preserve it.
            self.current_markers.clear()
        old_xlim = self.p1.ax.get_xlim() if preserve_view and not df.empty else None
        times_num = np.arange(len(df), dtype=float)
        for pane in panes:
            pane._format_index_time = True
            pane.plot(times_num, df, preserve_markers=preserve_view)
        if len(df):
            self._format_time_as_index = True
            xlim = old_xlim if old_xlim is not None else self.p1.ax.get_xlim()
            for pane in panes:
                pane.ax.set_xlim(xlim)
                pane.canvas._canvas.draw_idle()
            count = sum(len(pane.series) for pane in panes)
            mode = "Scaling ON" if self._scaling_enabled else "Recorded values"
            message = f"Showing {len(df)} of {len(self._last_df)} points for {count} plotted series | {mode}"
            if self._scaling_enabled and any(r.warning for r in self._scaling_results.values()):
                message += " | Conversion warnings: right-click Scaling factors for details"
            self.status.setText(message)
        else:
            self.status.setText("Drag variables to plots to load data. Scaling mode also applies to new plots.")
        self._update_scaling_ui()

    # ---------- marker mode toggles ----------
    def _on_marker_mode_toggled(self, checked):
        self.marker_mode_active = checked
        self.status.setText("Marker mode: Click on plots to place markers" if checked
                            else "Drag variables to plots to start | Click plot to sync crosshair | Wheel zoom Y")

    # ---------- index→window time helpers ----------
    def _format_marker_time(self, x_sample: float) -> str:
        if self._format_time_as_index and "timestamp" in self._last_df_shown.columns:
            sample_idx = int(round(x_sample))
            if 0 <= sample_idx < len(self._last_df_shown):
                ts = float(self._last_df_shown["timestamp"].iloc[sample_idx])
                unix_ts = ts - LV_OFFSET if self._loaded_epoch == "labview" else ts
                # Round the complete timestamp, so .9996 carries into the next
                # second instead of producing an impossible '.1000' suffix.
                dt_obj = datetime.fromtimestamp(round(unix_ts * 1000) / 1000)
                return dt_obj.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f"Sample {int(round(x_sample))}"

    def _add_marker(self, x):
        index = snap_sample(x, len(self._last_df_shown))
        if index is None:
            self.status.setText("Load plotted data before adding a marker.")
            return
        self.marker_counter += 1
        marker_id = self.marker_counter
        color = MARKER_COLORS[(marker_id - 1) % len(MARKER_COLORS)]
        stamp = self._format_marker_time(index)
        self.current_markers.append(MarkerSnapshot(float(index), marker_id, color, stamp))
        for pane in (self.p1, self.p2, self.p3):
            pane.add_marker(index, marker_id, color, time_text=stamp)
        self.status.setText(f"Added M{marker_id} at {stamp} | Values at displayed sample {index}")

    def _clear_all_markers(self):
        for pane in (self.p1, self.p2, self.p3):
            pane.clear_markers()
        self.current_markers.clear()
        self.marker_counter = 0
        self.status.setText("All markers cleared.")

    # ---------- viewer-only PDF export ----------
    def _export_pdf_dialog(self):
        panes = (self.p1, self.p2, self.p3)
        if self._last_df_shown.empty or not any(p._trace_snapshots for p in panes):
            QtWidgets.QMessageBox.information(self, "Export PDF", "Load data onto at least one plot first.")
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setObjectName("ExportDialog")
        dialog.setWindowTitle("Export plots to PDF")
        dialog.setMinimumWidth(420)
        form = QtWidgets.QVBoxLayout(dialog)
        form.setContentsMargins(20, 18, 20, 18)
        form.setSpacing(10)
        heading = QtWidgets.QLabel("Choose plots and report options")
        heading.setStyleSheet("font-size: 15px; font-weight: 600;")
        form.addWidget(heading)
        choices = []
        for pane in panes:
            checkbox = QtWidgets.QCheckBox(pane.title_lbl.text())
            checkbox.setChecked(bool(pane._trace_snapshots))
            checkbox.setEnabled(bool(pane._trace_snapshots))
            choices.append(checkbox)
            form.addWidget(checkbox)
        include = QtWidgets.QCheckBox("Include markers and marker-value table")
        include.setChecked(any(p._marker_specs for p in panes))
        form.addWidget(include)
        paper = QtWidgets.QCheckBox("Print-friendly colors (white background)")
        paper.setChecked(True)
        form.addWidget(paper)
        separate = QtWidgets.QCheckBox("One plot per page")
        form.addWidget(separate)
        help_text = QtWidgets.QLabel(
            "Uses the displayed samples, current scaling and current zoom.\n"
            "Uncheck print-friendly colors to retain the dark plot theme.\n"
            "Only markers inside the exported X range are included.")
        help_text.setObjectName("AppSubtitle")
        help_text.setWordWrap(True)
        form.addWidget(help_text)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("Save PDF…")
        def update_selection():
            buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setEnabled(
                any(c.isChecked() and c.isEnabled() for c in choices))
        for checkbox in choices:
            checkbox.toggled.connect(lambda _checked: update_selection())
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addWidget(buttons)
        update_selection()
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        selected = [p for p, c in zip(panes, choices) if c.isChecked() and c.isEnabled()]
        name = "CNL_record_plots_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".pdf"
        save = QtWidgets.QFileDialog(self, "Save plot report", os.path.join(self._last_pdf_dir, name))
        save.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        save.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        save.setNameFilter("PDF files (*.pdf)")
        save.setDefaultSuffix("pdf")  # Confirm overwrites with the final extension.
        if save.exec() != QtWidgets.QDialog.DialogCode.Accepted or not save.selectedFiles():
            return
        path = save.selectedFiles()[0]
        try:
            self.export_pdf_btn.setEnabled(False)
            pages = self._save_pdf(path, selected, include_markers=include.isChecked(),
                                   print_friendly=paper.isChecked(), one_plot_per_page=separate.isChecked())
        except Exception as exc:
            self._warn("PDF export failed", f"The report could not be saved.\n{exc}\n\n"
                       "Check the folder permissions, or close the destination PDF and try again.")
        else:
            self._last_pdf_dir = os.path.dirname(os.path.abspath(path))
            self.status.setText(f"Saved PDF ({pages} pages): {path}")
            QtWidgets.QMessageBox.information(self, "PDF saved", f"Saved {pages} page(s):\n{path}")
        finally:
            self.export_pdf_btn.setEnabled(True)

    def _save_pdf(self, path, panes, **options):
        snapshots = [pane.report_snapshot() for pane in panes]
        notes = []
        if self._scaling_enabled:
            notes.append("Scaled raw records use the currently loaded calibration, not a historical version. "
                         "Already-scaled engineering columns are not rescaled.")
            for kind, location in self._calibration.paths.items():
                notes.append(f"{kind} calibration: {location}")
        info = ReportInfo(
            database=self._loaded_db_path,
            start_time=self._format_marker_time(0),
            end_time=self._format_marker_time(len(self._last_df_shown) - 1),
            displayed_count=len(self._last_df_shown), loaded_count=len(self._last_df),
            scaling_mode="Scaling ON (engineering units)" if self._scaling_enabled else "Scaling OFF (recorded values)",
            notes=notes)
        logo = next((p for p in (
            os.environ.get("CNL_VIEWER_LOGO", ""), os.path.join(SCRIPT_DIR, "cnl_logo.png"),
            os.path.join(SCRIPT_DIR, "assets", "cnl_logo.png")) if p and os.path.isfile(p)), None)
        return export_pdf(path, snapshots, info, logo_path=logo, **options)

    def _update_crosshair(self, x, source_pane):
        self._current_crosshair_x = x
        for pane in (self.p1, self.p2, self.p3):
            if pane != source_pane:
                pane.update_crosshair(x)

    def _sync_crosshair_click(self, x):
        self._current_crosshair_x = x
        for pane in (self.p1, self.p2, self.p3):
            pane.update_crosshair(x)

    # ---------- load columns ----------
    def load_columns(self, autofit_window: bool = True):
        self.col_list.clear()
        try:
            with self._connect() as c:
                cols = pd.read_sql_query("PRAGMA table_info(channel_data)", c)
            names = list(cols["name"].astype(str))
        except Exception as e:
            self.status.setText(f"PRAGMA failed: {e}")
            names = []

        self._db_cols = set(names)

        for c in names:
            it = QtWidgets.QListWidgetItem(display_channel_labels(c))
            it.setData(QtCore.Qt.ItemDataRole.UserRole, c)
            it.setToolTip(f"SQLite column: {c}")
            it.setSelected(False)
            it.setFlags(it.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.col_list.addItem(it)

        self.status.setText(f"Loaded {len(names)} columns. Drag variables to plots.")

        if autofit_window:
            self.jump_to_latest(300)

    def jump_to_latest(self, safety_window_s: int = 300):
        mx = self._latest_timestamp()
        if mx is None:
            return
        unix = mx - LV_OFFSET if self._detect_db_epoch() == "labview" else mx
        end_dt = datetime.fromtimestamp(unix)
        start_dt = end_dt - timedelta(seconds=int(safety_window_s))

        self.start_dt.blockSignals(True)
        self.end_dt.blockSignals(True)
        self.start_dt.setDateTime(QtCore.QDateTime.fromSecsSinceEpoch(int(start_dt.timestamp())))
        self.end_dt.setDateTime(QtCore.QDateTime.fromSecsSinceEpoch(int(end_dt.timestamp())))
        self.start_dt.blockSignals(False)
        self.end_dt.blockSignals(False)

        self.run_query()

    def _on_browse(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open SQLite DB",
            self.db_edit.text().strip(),
            "SQLite DB (*.db *.sqlite *.sqlite3);;All files (*)"
        )
        if p:
            self.db_edit.setText(p)
            self.load_columns(autofit_window=True)

    def _after_drop(self, names: list, pane: PlotPane):
        changed = False
        for n in names:
            if n not in pane.series:
                pane.series.append(n)
                changed = True
        if changed:
            pane.changed.emit()
            self.run_query()

    def _sync_xlim_from(self, source_ax, *args):
        try:
            xlim = source_ax.get_xlim()
        except Exception:
            return
        for ax in (self.p1.ax, self.p2.ax, self.p3.ax):
            if ax is source_ax:
                continue
            if ax.get_xlim() != xlim:
                ax.set_xlim(xlim)
                ax.figure.canvas.draw_idle()

    def _check_window(self):
        try:
            with self._connect() as c:
                epoch = self._detect_db_epoch()
                s = self.start_dt.dateTime().toSecsSinceEpoch()
                e = self.end_dt.dateTime().toSecsSinceEpoch()
                if epoch == "labview":
                    s += LV_OFFSET; e += LV_OFFSET
                n = c.execute("SELECT COUNT(*) FROM channel_data WHERE timestamp BETWEEN ? AND ?;", (s, e)).fetchone()[0]
                latest = c.execute("SELECT MAX(timestamp) FROM channel_data;").fetchone()[0]
            msg = [f"Rows in window: {n}", f"Epoch mode: {epoch}"]
            if latest is not None:
                unix = float(latest) - (LV_OFFSET if epoch == "labview" else 0)
                msg.append(f"Latest row: {datetime.fromtimestamp(unix)}")
            QtWidgets.QMessageBox.information(self, "Window check", "\n".join(msg))
        except Exception as e:
            self._warn("Window check", str(e))

    # ---------- main query ----------
    def run_query(self):
        all_series = self.p1.series + self.p2.series + self.p3.series
        if not all_series:
            self.status.setText("Drag variables to plots to load data")
            self._last_df = pd.DataFrame()
            self._last_df_shown = pd.DataFrame()
            return

        # KEY FIX: expand SELECT columns so fallback columns exist in df
        cols_q = self._expand_needed_cols(all_series)

        time_clause = self._time_clause()
        try:
            with self._connect() as c:
                sql = f"SELECT {', '.join(cols_q)} {time_clause} ORDER BY timestamp ASC"
                df_full = pd.read_sql_query(sql, c)
        except Exception as e:
            self._warn("Query failed", str(e))
            return

        self._loaded_db_path = os.path.abspath(self.db_edit.text().strip())
        self._loaded_epoch = self._detect_db_epoch()
        self._last_df = df_full
        self._last_df_shown = self._decimate_uniform(df_full, int(self.points_n.value())).copy()
        self._render_current_data()
        if df_full.empty:
            self.status.setText("No rows in window. Use 'Check' or 'Jump to Latest'.")

# ---- standalone launcher ----
def launch(db_path: str = None):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    w = SQLiteLogViewer(db_path or (sys.argv[1] if len(sys.argv) > 1 else None))
    w.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(launch())
