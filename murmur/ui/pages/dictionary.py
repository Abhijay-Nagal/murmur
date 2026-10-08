from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QToolButton, QWidget,
)

from .. import theme
from ..icons import icon
from ..widgets import Page, SettingsCard, clear_layout, label


class FlowLayout(QLayout):
    """Lays children left to right, wrapping onto new lines (for word chips)."""

    def __init__(self, spacing: int = 8):
        super().__init__()
        self._items = []
        self._spacing = spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(QRect(0, 0, width, 0), dry=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, dry=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _layout(self, rect, dry):
        x, y, line_h = rect.x(), rect.y(), 0
        for item in self._items:
            w, h = item.sizeHint().width(), item.sizeHint().height()
            if x + w > rect.right() and line_h:
                x, y = rect.x(), y + line_h + self._spacing
                line_h = 0
            if not dry:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += w + self._spacing
            line_h = max(line_h, h)
        return y + line_h - rect.y()


class Chip(QWidget):
    def __init__(self, text: str, on_remove):
        super().__init__()
        self.setObjectName("Chip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 4, 4, 4)
        lay.setSpacing(4)
        lay.addWidget(label(text))
        x = QToolButton()
        x.setObjectName("Ghost")
        x.setIcon(icon("x", theme.FAINT, 14))
        x.setCursor(Qt.PointingHandCursor)
        x.setToolTip("Remove")
        x.clicked.connect(lambda: on_remove(text))
        lay.addWidget(x)


class DictionaryPage(Page):
    def __init__(self, app):
        super().__init__("Dictionary", "Teach Murmur your words, and set up text shortcuts.")
        self.app = app

        # ---- vocabulary ----
        vocab = SettingsCard(
            "Vocabulary", "book",
            "Names, brands and jargon Murmur should spell correctly, such as people's names, product names or "
            "course codes. This is the single best way to fix words it keeps mishearing.",
        )
        add_row = QHBoxLayout()
        self.word_in = QLineEdit()
        self.word_in.setPlaceholderText("Add a word or phrase, e.g. Kubernetes")
        self.word_in.returnPressed.connect(self.add_word)
        add = QPushButton("Add")
        add.setObjectName("Primary")
        add.clicked.connect(self.add_word)
        add_row.addWidget(self.word_in, 1)
        add_row.addWidget(add)
        vocab.body.addLayout(add_row)
        vocab.body.addSpacing(12)
        self.chips_host = QWidget()
        self.chips = FlowLayout(8)
        self.chips_host.setLayout(self.chips)
        vocab.body.addWidget(self.chips_host)
        self.body.addWidget(vocab)

        # ---- replacements ----
        rep = SettingsCard(
            "Shortcuts", "zap",
            "Say a phrase and Murmur types something else. For example, say “my email” to type your email "
            "address, or “sig” to type your signature.",
        )
        row = QHBoxLayout()
        self.say_in = QLineEdit()
        self.say_in.setPlaceholderText("When I say…")
        self.type_in = QLineEdit()
        self.type_in.setPlaceholderText("Type this…")
        self.type_in.returnPressed.connect(self.add_replacement)
        add2 = QPushButton("Add")
        add2.setObjectName("Primary")
        add2.clicked.connect(self.add_replacement)
        row.addWidget(self.say_in, 1)
        row.addWidget(self.type_in, 2)
        row.addWidget(add2)
        rep.body.addLayout(row)
        rep.body.addSpacing(12)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["When I say", "Murmur types", ""])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 44)
        self.table.itemChanged.connect(self._table_edited)
        rep.body.addWidget(self.table)
        self.body.addWidget(rep)

        # ---- voice commands reference ----
        cmds = SettingsCard("Voice commands", "mic", "Say these while dictating (turn them off in Settings).")
        for spoken, effect in (("“new line”", "Starts a new line"), ("“new paragraph”", "Starts a new paragraph"),
                               ("“no wait…”, “actually…”", "With AI cleanup on, keeps only your correction")):
            r = QHBoxLayout()
            s = label(spoken, "SectionTitle")
            s.setFixedWidth(220)
            r.addWidget(s)
            r.addWidget(label(effect, "Muted"), 1)
            cmds.body.addLayout(r)
            cmds.body.addSpacing(6)
        self.body.addWidget(cmds)
        self.finish()
        self.refresh()

    def refresh(self):
        clear_layout(self.chips)
        words = self.app.settings.vocabulary
        if not words:
            self.chips.addWidget(label("No words yet.", "Muted"))
        for w in words:
            self.chips.addWidget(Chip(w, self.remove_word))
        self.chips_host.updateGeometry()

        self.table.blockSignals(True)
        reps = self.app.settings.replacements
        self.table.setRowCount(len(reps))
        for i, (spoken, typed) in enumerate(reps):
            self.table.setItem(i, 0, QTableWidgetItem(spoken))
            self.table.setItem(i, 1, QTableWidgetItem(typed))
            b = QToolButton()
            b.setObjectName("Ghost")
            b.setIcon(icon("trash", theme.MUTED, 15))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, idx=i: self.remove_replacement(idx))
            self.table.setCellWidget(i, 2, b)
        self.table.setFixedHeight(42 + 40 * max(1, len(reps)))
        for i in range(len(reps)):
            self.table.setRowHeight(i, 40)
        self.table.blockSignals(False)

    def _update(self, fn):
        s = self.app.settings.copy()
        fn(s)
        self.app.update_settings(s)
        self.refresh()

    def add_word(self):
        w = self.word_in.text().strip()
        if w and w.lower() not in (v.lower() for v in self.app.settings.vocabulary):
            self._update(lambda s: s.vocabulary.append(w))
        self.word_in.clear()

    def remove_word(self, w):
        self._update(lambda s: s.vocabulary.remove(w))

    def add_replacement(self):
        spoken, typed = self.say_in.text().strip(), self.type_in.text()
        if spoken and typed:
            self._update(lambda s: s.replacements.append([spoken, typed]))
            self.say_in.clear()
            self.type_in.clear()
            self.say_in.setFocus()

    def remove_replacement(self, idx):
        self._update(lambda s: s.replacements.pop(idx))

    def _table_edited(self, item):
        def fn(s):
            s.replacements[item.row()][item.column()] = item.text()
        s = self.app.settings.copy()
        fn(s)
        self.app.update_settings(s)
