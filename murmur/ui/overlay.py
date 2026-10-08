"""The floating pill at the bottom of the screen that shows Murmur is listening.

It must never take keyboard focus, or the paste would land in the pill instead of the
user's app, so it is a no-activate, click-through tool window.
"""
import collections
import ctypes
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from . import theme

W, H = 268, 46
BARS = 22


class Overlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(W, H)
        self.mode = "hidden"  # recording | hands_free | processing | notice
        self.message = ""
        self.levels = collections.deque([0.0] * BARS, maxlen=BARS)
        self._phase = 0.0
        self._timer = QTimer(self, interval=33, timeout=self._tick)
        self._hide_timer = QTimer(self, singleShot=True, timeout=self.hide)
        self.enabled = True

    def _make_noactivate(self):
        # Belt and braces for Windows: WS_EX_NOACTIVATE | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x08000000 | 0x20 | 0x80)

    def _place(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        g = screen.availableGeometry()
        self.move(g.center().x() - W // 2, g.bottom() - H - 28)

    def show_state(self, state: str):
        if not self.enabled:
            return
        if state in ("recording", "hands_free", "processing"):
            self._hide_timer.stop()
            if state != "processing" and self.mode not in ("recording", "hands_free"):
                self.levels.extend([0.0] * BARS)
            self.mode = state
            self._place()
            if not self.isVisible():
                self.show()
                self._make_noactivate()
            self._timer.start()
            self.update()
        elif self.mode != "notice":
            self.mode = "hidden"
            self._timer.stop()
            self.hide()

    def show_notice(self, text: str):
        if not self.enabled:
            return
        self.mode, self.message = "notice", text
        self._timer.stop()
        self._place()
        self.show()
        self._make_noactivate()
        self.update()
        self._hide_timer.start(2600)

    def hideEvent(self, e):
        if self.mode == "notice":
            self.mode = "hidden"
        super().hideEvent(e)

    def push_level(self, v: float):
        if self.mode in ("recording", "hands_free"):
            self.levels.append(v)

    def _tick(self):
        self._phase += 0.18
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(1, 1, W - 2, H - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, H / 2, H / 2)
        p.fillPath(path, QColor(42, 29, 21, 242))
        p.setPen(QColor(224, 161, 90, 70))
        p.drawPath(path)

        if self.mode == "notice":
            p.setPen(QColor(theme.SIDE_TEXT))
            f = QFont("Segoe UI", 9)
            p.setFont(f)
            p.drawText(rect.adjusted(16, 0, -16, 0), Qt.AlignCenter | Qt.TextWordWrap, self.message)
            return

        # left: status dot (pulsing while recording) or spinner while processing
        cx, cy = 24, H / 2
        if self.mode == "processing":
            for i in range(8):
                a = self._phase * 1.6 + i * math.pi / 4
                c = QColor(theme.AMBER)
                c.setAlpha(int(40 + 215 * ((i / 8))))
                p.setPen(Qt.NoPen)
                p.setBrush(c)
                p.drawEllipse(QPointF(cx + 8 * math.cos(a), cy + 8 * math.sin(a)), 2, 2)
        else:
            pulse = 0.5 + 0.5 * math.sin(self._phase * 0.9)
            glow = QColor(theme.RECORD)
            glow.setAlpha(int(50 + 60 * pulse))
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(QPointF(cx, cy), 9, 9)
            p.setBrush(QColor(theme.RECORD))
            p.drawEllipse(QPointF(cx, cy), 5, 5)

        # middle: waveform bars
        x0, x1 = 44, W - (96 if self.mode == "hands_free" else 22)
        bw = (x1 - x0) / BARS
        grad = QLinearGradient(x0, 0, x1, 0)
        grad.setColorAt(0, QColor("#f3d2a2"))
        grad.setColorAt(0.5, QColor(theme.AMBER))
        grad.setColorAt(1, QColor("#d9703f"))
        p.setBrush(grad)
        for i, lv in enumerate(self.levels):
            if self.mode == "processing":
                lv = 0.25 + 0.2 * math.sin(self._phase + i * 0.5)
            h = max(3.0, lv * (H - 18))
            p.drawRoundedRect(QRectF(x0 + i * bw + bw * 0.2, cy - h / 2, bw * 0.6, h), 1.5, 1.5)

        if self.mode == "hands_free":
            p.setPen(QColor(theme.SIDE_MUTED))
            p.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
            p.drawText(QRectF(W - 92, 0, 78, H), Qt.AlignVCenter | Qt.AlignRight, "HANDS-FREE")
