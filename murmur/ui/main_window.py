from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QMainWindow, QPushButton, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from . import theme
from .icons import icon, logo_icon
from .pages.about import AboutPage
from .pages.dictionary import DictionaryPage
from .pages.history import HistoryPage
from .pages.home import STATE_TEXT, HomePage
from .pages.settings_page import SettingsPage
from .widgets import StatusDot, label

NAV = [
    ("home", "Home", "home"),
    ("history", "History", "history"),
    ("dictionary", "Dictionary", "book"),
    ("settings", "Settings", "settings"),
    ("about", "About", "info"),
]


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Murmur")
        self.setWindowIcon(logo_icon())
        self.resize(1060, 720)
        self.setMinimumSize(860, 560)

        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.setCentralWidget(root)

        # ---------- sidebar ----------
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setAttribute(Qt.WA_StyledBackground, True)
        side.setFixedWidth(224)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 26, 0, 0)
        sl.setSpacing(2)
        brand = QVBoxLayout()
        brand.setContentsMargins(22, 0, 16, 0)
        brand.setSpacing(0)
        brand.addWidget(label("Murmur", "Brand"))
        brand.addWidget(label("speak, and it's written", "BrandTag"))
        sl.addLayout(brand)
        sl.addSpacing(30)

        self.pages = QStackedWidget()
        self.page_by_key = {
            "home": HomePage(app),
            "history": HistoryPage(app),
            "dictionary": DictionaryPage(app),
            "settings": SettingsPage(app),
            "about": AboutPage(app),
        }
        self.page_by_key["home"].open_page.connect(self.show_page)
        self.buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        for key, text, ico in NAV:
            b = QPushButton(f"  {text}")
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(icon(ico, theme.SIDE_MUTED, 17))
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            group.addButton(b)
            sl.addWidget(b)
            self.buttons[key] = b
            self.pages.addWidget(self.page_by_key[key])
        sl.addStretch(1)

        # status card at the bottom of the sidebar
        status = QWidget()
        status.setObjectName("SidebarStatus")
        status.setAttribute(Qt.WA_StyledBackground, True)
        st = QHBoxLayout(status)
        st.setContentsMargins(20, 14, 12, 16)
        st.setSpacing(8)
        self.dot = StatusDot(theme.SIDE_MUTED)
        st.addWidget(self.dot)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.status_text = label("Starting up", "SideStatus")
        self.status_sub = label("", "Faint")
        col.addWidget(self.status_text)
        col.addWidget(self.status_sub)
        st.addLayout(col, 1)
        self.pause_btn = QToolButton()
        self.pause_btn.setObjectName("Ghost")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setIcon(icon("pause", theme.SIDE_MUTED, 15))
        self.pause_btn.setToolTip("Pause dictation")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.toggled.connect(app.set_paused)
        st.addWidget(self.pause_btn)
        sl.addWidget(status)

        lay.addWidget(side)
        lay.addWidget(self.pages, 1)
        self.show_page("home")

    def show_page(self, key: str):
        self.buttons[key].setChecked(True)
        for k, b in self.buttons.items():
            b.setIcon(icon(dict((n[0], n[2]) for n in NAV)[k], theme.AMBER if k == key else theme.SIDE_MUTED, 17))
        page = self.page_by_key[key]
        if hasattr(page, "refresh"):
            page.refresh()
        page.scroll_top()
        if key == "settings":
            page.check_ollama()
        self.pages.setCurrentWidget(page)

    def set_state(self, state: str, detail: str):
        self.dot.set_color(theme.STATE_COLORS.get(state, theme.MUTED))
        self.status_text.setText(STATE_TEXT.get(state, state))
        sub = self.app.settings.hotkey_label
        if state == "loading":
            sub = detail or "Loading model…"
        elif state == "paused":
            sub = "Hotkey disabled"
        elif state == "error":
            sub = "See Settings"
        self.status_sub.setText(sub)
        self.status_sub.setToolTip(detail)
        self.pause_btn.blockSignals(True)
        self.pause_btn.setChecked(state == "paused")
        self.pause_btn.blockSignals(False)
        self.page_by_key["home"].set_state(state, detail)

    def closeEvent(self, e):
        # Closing the window keeps Murmur running in the tray, like other dictation apps.
        e.ignore()
        self.hide()
        self.app.first_hide_hint()
