"""Reusable building blocks: cards, setting rows, toggle switches, stat tiles, level meter."""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton, QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from . import theme
from .icons import icon


def clear_layout(layout):
    """Remove everything from a layout right away. deleteLater alone leaves the old widgets
    on screen until the event loop runs, so a quick refresh would draw both sets."""
    while layout.count():
        item = layout.takeAt(0)
        if w := item.widget():
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif sub := item.layout():
            clear_layout(sub)


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


class Card(QFrame):
    def __init__(self, name: str = "Card", padding: int = 20, spacing: int = 12):
        super().__init__()
        self.setObjectName(name)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)


class Page(QWidget):
    """A scrollable page with a title and subtitle."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        inner = QWidget()
        inner.setObjectName("Content")
        scroll.setWidget(inner)
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(44, 34, 44, 40)
        self.body.setSpacing(18)
        head = QVBoxLayout()
        head.setSpacing(2)
        self.title = label(title, "PageTitle")
        head.addWidget(self.title)
        if subtitle:
            head.addWidget(label(subtitle, "PageSubtitle", wrap=True))
        self.body.addLayout(head)
        self.body.addSpacing(8)

    def finish(self):
        self.body.addStretch(1)

    def scroll_top(self):
        self.scroll.verticalScrollBar().setValue(0)


class Toggle(QAbstractButton):
    """An animated on/off switch."""

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on: bool):
        self._anim.stop()
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def _get_knob(self):
        return self._pos

    def _set_knob(self, v):
        self._pos = v
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def sizeHint(self):
        return QSize(42, 24)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        off, on = QColor(theme.TOGGLE_OFF), QColor(theme.ACCENT)
        track = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
        )
        if not self.isEnabled():
            track.setAlpha(110)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, 42, 24), 12, 12)
        p.setBrush(QColor(theme.INPUT))
        p.drawEllipse(QRectF(3 + self._pos * 18, 3, 18, 18))


class SettingRow(QWidget):
    """Title + description on the left, a control on the right."""

    def __init__(self, title: str, description: str, control: QWidget, first: bool = False):
        super().__init__()
        if not first:
            self.setObjectName("Row")
            self.setAttribute(Qt.WA_StyledBackground, True)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 12, 0, 12)
        row.setSpacing(24)
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(label(title, "SectionTitle"))
        self.desc = label(description, "Muted", wrap=True)
        self.desc.setVisible(bool(description))
        text.addWidget(self.desc)
        row.addLayout(text, 1)
        row.addWidget(control, 0, Qt.AlignVCenter | Qt.AlignRight)
        self.control = control


class SettingsCard(Card):
    def __init__(self, title: str, icon_name: str, description: str = ""):
        super().__init__(padding=20, spacing=0)
        head = QHBoxLayout()
        head.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(icon(icon_name, theme.ACCENT, 17).pixmap(17, 17))
        head.addWidget(ico, 0, Qt.AlignVCenter)
        head.addWidget(label(title, "CardTitle"))
        head.addStretch(1)
        self.body.addLayout(head)
        if description:
            self.body.addSpacing(4)
            self.body.addWidget(label(description, "Muted", wrap=True))
        self.body.addSpacing(8)
        self._rows = 0

    def add(self, title: str, description: str, control: QWidget) -> QWidget:
        row = SettingRow(title, description, control, first=self._rows == 0)
        self.body.addWidget(row)
        self._rows += 1
        self.last_row = row
        return control

    def add_widget(self, w: QWidget):
        self.body.addWidget(w)


class StatCell(QWidget):
    """One column of the stats ledger: small caps caption, a big serif number, a note."""

    def __init__(self, caption: str, first: bool = False):
        super().__init__()
        if not first:
            self.setObjectName("StatCell")
            self.setAttribute(Qt.WA_StyledBackground, True)
        body = QVBoxLayout(self)
        body.setContentsMargins(0 if first else 22, 2, 12, 2)
        body.setSpacing(2)
        body.addWidget(label(caption.upper(), "StatLabel"))
        self.value = label("—", "StatValue")
        body.addWidget(self.value)
        self.hint = label("", "Faint")
        body.addWidget(self.hint)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


class Badge(QLabel):
    def __init__(self, text: str = "", color: str = theme.MUTED):
        super().__init__(text)
        self.setObjectName("Badge")
        self.set(text, color)

    def set(self, text: str, color: str):
        self.setText(text)
        c = QColor(color)
        self.setStyleSheet(
            f"color: {color}; background: rgba({c.red()},{c.green()},{c.blue()},0.13);"
        )


class StatusDot(QWidget):
    def __init__(self, color: str = theme.MUTED, size: int = 9):
        super().__init__()
        self._color = QColor(color)
        self.setFixedSize(size + 6, size + 6)
        self._size = size

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        glow = QColor(self._color)
        glow.setAlpha(60)
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(0, 0, self.width(), self.height()))
        p.setBrush(self._color)
        o = (self.width() - self._size) / 2
        p.drawEllipse(QRectF(o, o, self._size, self._size))


class LevelMeter(QWidget):
    """Segmented live microphone level."""

    def __init__(self, segments: int = 28):
        super().__init__()
        self.segments = segments
        self.value = 0.0
        self.setFixedHeight(14)
        self.setMinimumWidth(200)

    def set_level(self, v: float):
        # Fast attack, slow release, so the meter reads steadily.
        self.value = v if v > self.value else self.value * 0.85 + v * 0.15
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        gap = 3
        w = (self.width() - gap * (self.segments - 1)) / self.segments
        lit = round(self.value * self.segments)
        for i in range(self.segments):
            frac = i / self.segments
            if i < lit:
                color = QColor(theme.SUCCESS if frac < 0.65 else theme.WARNING if frac < 0.85 else theme.DANGER)
            else:
                color = QColor(theme.BORDER)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(i * (w + gap), 0, w, self.height()), 2, 2)


class Keycap(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("Keycap")
        self.setAlignment(Qt.AlignCenter)


def hbox(*widgets, spacing: int = 8, stretch_end: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        if isinstance(w, int):
            lay.addSpacing(w)
        elif w is None:
            lay.addStretch(1)
        else:
            lay.addWidget(w)
    if stretch_end:
        lay.addStretch(1)
    return lay


class ClickableCard(Card):
    clicked = Signal()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
