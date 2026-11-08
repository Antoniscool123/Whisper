from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout


def make_icon(name: str, color: str = "#B7C9DA", size: int = 24) -> QIcon:
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(2, 2)
    pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    if name == "mic":
        painter.drawRoundedRect(QRectF(8, 3, 8, 12), 4, 4)
        path = QPainterPath(QPointF(5, 11)); path.cubicTo(5, 21, 19, 21, 19, 11)
        painter.drawPath(path); painter.drawLine(12, 19, 12, 22); painter.drawLine(8, 22, 16, 22)
    elif name == "stop":
        painter.setBrush(QColor(color)); painter.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)
    elif name == "history":
        painter.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 290 * 16)
        painter.drawLine(12, 7, 12, 12); painter.drawLine(12, 12, 16, 14)
        painter.drawLine(3, 4, 3, 9); painter.drawLine(3, 9, 8, 9)
    elif name == "book":
        painter.drawRoundedRect(QRectF(4, 3, 16, 18), 2, 2)
        painter.drawLine(8, 3, 8, 21)
        painter.drawLine(11, 8, 17, 8); painter.drawLine(11, 12, 16, 12)
    elif name == "settings":
        for y, x in ((6, 15), (12, 8), (18, 17)):
            painter.drawLine(4, y, 20, y); painter.drawEllipse(QPointF(x, y), 2.3, 2.3)
    elif name == "shield":
        path = QPainterPath(QPointF(12, 2)); path.lineTo(20, 6); path.lineTo(19, 14)
        path.quadTo(17, 20, 12, 22); path.quadTo(7, 20, 5, 14); path.lineTo(4, 6); path.closeSubpath()
        painter.drawPath(path); painter.drawLine(8, 12, 11, 15); painter.drawLine(11, 15, 16, 9)
    elif name == "copy":
        painter.drawRoundedRect(QRectF(8, 8, 12, 13), 2, 2)
        painter.drawLine(15, 5, 15, 3); painter.drawLine(15, 3, 4, 3); painter.drawLine(4, 3, 4, 16); painter.drawLine(4, 16, 6, 16)
    elif name == "insert":
        painter.drawLine(4, 12, 19, 12); painter.drawLine(14, 7, 19, 12); painter.drawLine(19, 12, 14, 17)
        painter.drawLine(4, 5, 4, 19)
    elif name == "download":
        painter.drawLine(12, 3, 12, 15); painter.drawLine(7, 10, 12, 15); painter.drawLine(12, 15, 17, 10)
        path = QPainterPath(QPointF(4, 16)); path.lineTo(4, 21); path.lineTo(20, 21); path.lineTo(20, 16)
        painter.drawPath(path)
    elif name == "check":
        painter.drawLine(5, 12, 10, 17); painter.drawLine(10, 17, 20, 6)
    elif name == "close":
        painter.drawLine(6, 6, 18, 18); painter.drawLine(18, 6, 6, 18)
    elif name == "globe":
        painter.drawEllipse(QRectF(3, 3, 18, 18)); painter.drawEllipse(QRectF(8, 3, 8, 18))
        painter.drawLine(3, 12, 21, 12)
    painter.end()
    return QIcon(pixmap)


class Card(QFrame):
    def __init__(self, object_name: str = "Card", margins=(20, 18, 20, 18), spacing: int = 12):
        super().__init__()
        self.setObjectName(object_name)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(*margins)
        self.layout_.setSpacing(spacing)


class Waveform(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(44)
        self.setMaximumHeight(52)
        self.levels = deque([0.03] * 64, maxlen=64)
        self.recording = False
        self.phase = 0.0

    def push(self, level: float, recording: bool) -> None:
        self.recording = recording
        self.phase += 0.16
        self.levels.append(max(0.035, level) if recording else 0.035)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        count = len(self.levels)
        step = width / count
        for index, level in enumerate(self.levels):
            if self.recording:
                color = QColor("#5EEAD4") if level > 0.08 else QColor("#3D817C")
                tall = 4 + level * (height - 7)
            else:
                color = QColor("#355763")
                tall = 4 + 5 * (0.5 + 0.5 * math.sin(index * 0.48))
            painter.setPen(Qt.NoPen); painter.setBrush(color)
            painter.drawRoundedRect(QRectF(index * step + 1, (height - tall) / 2, max(2, step - 3), tall), 2, 2)
        painter.end()


class StatusPill(QLabel):
    def __init__(self, text: str = "Local engine"):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(text, "#5EEAD4")

    def set_status(self, text: str, color: str = "#5EEAD4") -> None:
        self.setText(text)
        self.setStyleSheet(f"color: {color}; background: #172C32; border: 1px solid #2A454C; border-radius: 12px; padding: 6px 12px; font-size: 11px; font-weight: 600;")
