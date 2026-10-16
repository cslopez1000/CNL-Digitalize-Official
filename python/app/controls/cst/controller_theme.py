# -*- coding: utf-8 -*-
"""Shared Tesla-style widgets and colors for the cyclotron controller GUI."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Iterable, Sequence

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QTabBar, QWidget


@dataclass(frozen=True)
class Theme:
    window: str = "#070B0E"
    panel: str = "#0B1116"
    panel_2: str = "#0D151B"
    border: str = "#27323A"
    border_soft: str = "#1B252C"
    text: str = "#E8EDF0"
    muted: str = "#AAB5BC"
    dim: str = "#74818A"
    cyan: str = "#69BDF7"
    cyan_bright: str = "#78C9FF"
    green: str = "#62E873"
    orange: str = "#F49A28"
    red: str = "#EF5A5A"
    amber: str = "#F4C65A"


T = Theme()


CONTROLLER_QSS = f"""
QWidget {{
    background: {T.window};
    color: {T.text};
    font-family: 'Segoe UI';
    font-size: 13px;
}}
QToolTip {{
    background: #131A20;
    color: {T.text};
    border: 1px solid {T.border};
    padding: 5px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #34414A;
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QTableWidget {{
    background: #0A1014;
    alternate-background-color: #0C1318;
    border: 1px solid {T.border};
    border-radius: 8px;
    gridline-color: #202B32;
    selection-background-color: #183148;
    selection-color: white;
}}
QHeaderView::section {{
    background: #10171C;
    color: {T.muted};
    border: none;
    border-bottom: 1px solid {T.border};
    padding: 8px;
    font-weight: 600;
}}
QDoubleSpinBox, QSpinBox, QComboBox {{
    background: #0E151A;
    color: {T.text};
    border: 1px solid #3A4851;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 24px;
}}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {T.cyan};
}}
QCheckBox {{
    color: {T.text};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid #566772;
    border-radius: 4px;
    background: #0E151A;
}}
QCheckBox::indicator:checked {{
    background: {T.cyan};
    border-color: {T.cyan};
}}
"""


class Card(QFrame):
    """Simple flat Tesla-style card."""

    def __init__(self, parent: QWidget | None = None, radius: int = 10):
        super().__init__(parent)
        self.setObjectName("teslaCard")
        self.setStyleSheet(
            f"""
            QFrame#teslaCard {{
                background: {T.panel};
                border: 1px solid {T.border};
                border-radius: {radius}px;
            }}
            """
        )


class TeslaTabBar(QTabBar):
    """Flat tabs with a thin cyan selected indicator."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setStyleSheet(
            f"""
            QTabBar {{ background: transparent; }}
            QTabBar::tab {{
                background: transparent;
                color: {T.muted};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 12px 22px 10px 22px;
                min-width: 96px;
                font-size: 13px;
                font-weight: 500;
            }}
            QTabBar::tab:hover {{ color: {T.text}; }}
            QTabBar::tab:selected {{
                color: white;
                border-bottom: 3px solid {T.cyan};
            }}
            """
        )


class StatusDot(QWidget):
    def __init__(self, color: str = T.green, diameter: int = 12, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(diameter, diameter)

    def set_color(self, color: str | QColor) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))


class PlotToggle(QPushButton):
    """Independent circular plot-selection toggle."""

    selected = Signal(int, bool)

    def __init__(self, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.index = int(index)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.clicked.connect(lambda checked: self.selected.emit(self.index, bool(checked)))
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: 1px solid #8A9AA4;
                border-radius: 11px;
                margin: 5px;
            }}
            QPushButton:hover {{ border-color: {T.cyan}; }}
            QPushButton:checked {{
                background: {T.cyan};
                border: 4px solid #15242E;
            }}
            """
        )


class ClickLabel(QLabel):
    clicked = Signal(int)

    def __init__(self, index: int, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.index = int(index)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


from python.app.widgets.CstManualWidget import CstManualWidget as TrendPlot


def load_cnl_logo_pixmap(base_dir: str) -> QPixmap:
    """Load the replaceable CNL logo from the controller directory."""
    search_paths = (
        os.path.join(base_dir, "cnl_logo.png"),
        os.path.join(base_dir, "cnl_logo(2).png"),
        os.path.join(base_dir, "icons", "cnl_logo.png"),
        os.path.join(base_dir, "icons", "cnl_logo(2).png"),
    )
    for path in search_paths:
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap
    return QPixmap()


def secondary_button_css(accent: str = T.cyan) -> str:
    return f"""
        QPushButton {{
            background: #11191F;
            color: {T.text};
            border: 1px solid #3A4851;
            border-radius: 7px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover {{ background: #172129; border-color: {accent}; }}
        QPushButton:pressed, QPushButton:checked {{ background: #20303B; border-color: {accent}; }}
        QPushButton:disabled {{ color: #59646B; border-color: #293239; }}
    """


def bulk_button_css(accent: str) -> str:
    return f"""
        QPushButton {{
            background: #10171C;
            color: {accent};
            border: 1px solid #35434C;
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 10px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: #172129; border-color: {accent}; }}
        QPushButton:pressed {{ background: #20303B; }}
        QPushButton:disabled {{ color: #59646B; border-color: #293239; }}
    """


def target_label_css(selected: bool) -> str:
    border = T.cyan if selected else "#3C4B55"
    background = "#111C24" if selected else "#0E151A"
    return f"""
        QLabel {{
            color: {T.cyan};
            background: {background};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 7px;
            font-size: 17px;
            font-weight: 600;
        }}
    """


def state_button_css(accent: str, active: bool) -> str:
    background = "#172128" if active else "#10171C"
    return f"""
        QPushButton {{
            color: {accent};
            background: {background};
            border: 1px solid #35434C;
            border-radius: 6px;
            padding: 7px;
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton:hover {{ border-color: {accent}; }}
        QPushButton:disabled {{ color: #59646B; border-color: #293239; }}
    """


def digit_button_css() -> str:
    return f"""
        QPushButton {{
            background: #10171C;
            color: white;
            border: 1px solid #394750;
            border-radius: 7px;
            font-size: 27px;
        }}
        QPushButton:hover {{ background: #172129; border-color: {T.cyan}; }}
        QPushButton:pressed {{ background: #20303B; }}
    """


def info_label_css(accent: str = T.border) -> str:
    return f"""
        QLabel {{
            color: {T.muted};
            background: #0E151A;
            border: 1px solid {accent};
            border-radius: 7px;
            padding: 9px;
        }}
    """


def flat_button_css() -> str:
    return f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {T.text};
            font-size: 20px;
        }}
        QPushButton:hover {{ color: {T.cyan}; }}
    """


__all__ = [
    "T",
    "CONTROLLER_QSS",
    "Card",
    "TeslaTabBar",
    "StatusDot",
    "PlotToggle",
    "ClickLabel",
    "TrendPlot",
    "load_cnl_logo_pixmap",
    "secondary_button_css",
    "bulk_button_css",
    "target_label_css",
    "state_button_css",
    "digit_button_css",
    "info_label_css",
    "flat_button_css",
]
