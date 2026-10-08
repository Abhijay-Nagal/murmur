from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QToolButton, QVBoxLayout, QWidget,
)

from .. import theme
from ..icons import icon
from ..widgets import Card, Page, clear_layout, label


def _day_label(d) -> str:
    today = datetime.now().date()
    if d == today:
        return "Today"
    if d == today - timedelta(days=1):
        return "Yesterday"
    return d.strftime("%A, %d %B").replace(" 0", " ")


class HistoryItem(QWidget):
    def __init__(self, page, d, show_raw: bool):
        super().__init__()
        self.setObjectName("Row")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 12)
        lay.setSpacing(14)
        time_lbl = label(d.ts.strftime("%I:%M %p").lstrip("0"), "Faint")
        time_lbl.setFixedWidth(64)
        lay.addWidget(time_lbl, 0, Qt.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(3)
        body = label(d.final, wrap=True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        texts.addWidget(body)
        meta = []
        if d.app:
            meta.append(d.app)
        meta.append(f"{d.words} words · {d.audio_seconds:.0f}s")
        texts.addWidget(label("  ·  ".join(meta), "Faint"))
        if show_raw and d.raw.strip() != d.final.strip():
            raw = label(f"Heard: {d.raw}", "Faint", wrap=True)
            raw.setStyleSheet("font-style: italic;")
            texts.addWidget(raw)
        lay.addLayout(texts, 1)
        for ico, tip, fn in (("copy", "Copy", lambda: page.copy(d)), ("trash", "Delete", lambda: page.delete(d))):
            b = QToolButton()
            b.setObjectName("Ghost")
            b.setIcon(icon(ico, theme.MUTED, 16))
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            lay.addWidget(b, 0, Qt.AlignTop)


class HistoryPage(Page):
    def __init__(self, app):
        super().__init__("History", "Everything you've dictated, stored only on this computer.")
        self.app = app
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search your dictations…")
        self.search.addAction(icon("search", theme.FAINT, 16), QLineEdit.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        self._debounce = QTimer(self, singleShot=True, interval=200, timeout=self.refresh)
        self.search.textChanged.connect(lambda: self._debounce.start())
        bar.addWidget(self.search, 1)
        self.raw_btn = QPushButton("Show what Whisper heard")
        self.raw_btn.setCheckable(True)
        self.raw_btn.toggled.connect(self.refresh)
        bar.addWidget(self.raw_btn)
        clear = QPushButton("Clear all")
        clear.setObjectName("Danger")
        clear.clicked.connect(self.clear)
        bar.addWidget(clear)
        self.body.addLayout(bar)

        self.list_card = Card(padding=20, spacing=0)
        self.body.addWidget(self.list_card)
        self.toast = label("", "Faint")
        self.body.addWidget(self.toast)
        self.finish()
        self.refresh()

    def refresh(self):
        lay = self.list_card.body
        clear_layout(lay)
        items = self.app.storage.recent(300, self.search.text().strip())
        if not items:
            msg = "No matches." if self.search.text() else "No dictations yet."
            lay.addWidget(label(msg, "Muted"))
            return
        day = None
        for d in items:
            if d.ts.date() != day:
                day = d.ts.date()
                head = label(_day_label(day).upper(), "Faint")
                head.setStyleSheet("font-weight: 700; letter-spacing: 1px; padding-top: 10px;")
                lay.addWidget(head)
            lay.addWidget(HistoryItem(self, d, self.raw_btn.isChecked()))

    def copy(self, d):
        QApplication.clipboard().setText(d.final)
        self.toast.setText("Copied to clipboard")
        QTimer.singleShot(1800, lambda: self.toast.setText(""))

    def delete(self, d):
        self.app.storage.delete(d.id)
        self.refresh()
        self.app.stats_changed()

    def clear(self):
        if QMessageBox.question(self, "Clear history", "Delete all dictation history? This can't be undone.") \
                == QMessageBox.Yes:
            self.app.storage.clear()
            self.refresh()
            self.app.stats_changed()
