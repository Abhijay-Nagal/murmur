"""Murmur application: wires the engine, the window, the floating overlay and the tray icon."""
import logging
import os
import sys

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import winintegration
from .paths import LOG_PATH
from .settings import Settings
from .storage import Storage

log = logging.getLogger("murmur")
SERVER_NAME = "murmur-dictation-" + os.environ.get("USERNAME", "user")


def _setup_logging():
    # Under pythonw there is no console: stdout/stderr are None and any write would crash.
    if sys.stderr is None:
        sys.stdout = sys.stderr = open(os.devnull, "w")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
    )
    for noisy in ("httpx", "huggingface_hub", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _signal_running_instance() -> bool:
    """If Murmur is already running, ask it to show its window and return True."""
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


class MurmurApp(QObject):
    def __init__(self, qapp: QApplication, minimized: bool):
        super().__init__()
        from .engine.controller import Engine
        from .ui import theme
        from .ui.icons import logo_icon
        from .ui.main_window import MainWindow
        from .ui.overlay import Overlay

        self.qapp = qapp
        self.theme = theme
        self.settings = Settings.load()
        self.storage = Storage()
        self.engine = Engine(self.settings.copy(), self.storage)
        self._hint_shown = False

        self.overlay = Overlay()
        self.overlay.enabled = self.settings.overlay
        self.window = MainWindow(self)

        # ---- tray ----
        self._logo_icon = logo_icon
        self.tray = QSystemTrayIcon(logo_icon(theme.MUTED))
        self.tray.setToolTip("Murmur: starting up")
        menu = QMenu()
        menu.addAction("Open Murmur", self.show_window)
        self.pause_action = QAction("Pause dictation", menu, checkable=True)
        self.pause_action.toggled.connect(self.set_paused)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction("Quit Murmur", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.show_window() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

        # ---- engine signals (queued onto the UI thread) ----
        q = Qt.QueuedConnection
        self.engine.state_changed.connect(self._on_state, q)
        self.engine.level.connect(self._on_level, q)
        self.engine.dictated.connect(self._on_dictated, q)
        self.engine.notice.connect(self._on_notice, q)
        self.engine.start()

        # ---- single instance: later launches just bring this window forward ----
        QLocalServer.removeServer(SERVER_NAME)
        self.server = QLocalServer()
        self.server.listen(SERVER_NAME)
        self.server.newConnection.connect(self._on_second_launch)

        if not minimized:
            self.show_window()
        # Check Ollama shortly after start so the Home page can suggest setup.
        QTimer.singleShot(1500, self.window.page_by_key["settings"].check_ollama)

    # ---------- window / tray ----------
    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_second_launch(self):
        conn = self.server.nextPendingConnection()
        if conn:
            conn.waitForReadyRead(300)
            conn.close()
        self.show_window()

    def first_hide_hint(self):
        if not self._hint_shown:
            self._hint_shown = True
            self.notify("Murmur is still running in the tray. Hold your hotkey anywhere to dictate.")

    def notify(self, message: str):
        self.tray.showMessage("Murmur", message, self._logo_icon(), 4000)

    # ---------- engine events ----------
    def _on_state(self, state: str, detail: str):
        color = self.theme.STATE_COLORS.get(state, self.theme.MUTED)
        self.tray.setIcon(self._logo_icon(color))
        labels = {"ready": f"ready. Hold {self.settings.hotkey_label} to dictate", "recording": "listening…",
                  "hands_free": "listening (hands-free)…", "processing": "transcribing…",
                  "paused": "paused", "loading": detail or "loading…", "error": f"error: {detail}"}
        self.tray.setToolTip(f"Murmur: {labels.get(state, state)}"[:127])
        self.window.set_state(state, detail)
        self.overlay.show_state(state)
        self.pause_action.blockSignals(True)
        self.pause_action.setChecked(state == "paused")
        self.pause_action.blockSignals(False)
        if state == "error":
            self.notify(f"Murmur couldn't start: {detail}")
        if state == "ready":
            self.window.page_by_key["about"].refresh()

    def _on_dictated(self, _dictation):
        self.stats_changed()

    def _on_level(self, v: float):
        self.overlay.push_level(v)
        self.window.page_by_key["settings"].push_level(v)

    def _on_notice(self, text: str):
        if self.settings.overlay:
            self.overlay.show_notice(text)
        else:
            self.notify(text)

    # ---------- called by pages ----------
    def update_settings(self, new: Settings):
        self.settings = new
        new.save()
        self.overlay.enabled = new.overlay
        self.engine.apply_settings(new.copy())
        self.window.page_by_key["home"].refresh()
        self.window.set_state(self.engine.state, "")

    def set_paused(self, paused: bool):
        self.engine.set_paused(paused)

    def stats_changed(self):
        page = self.window.pages.currentWidget()
        if hasattr(page, "refresh") and page is not self.window.page_by_key["settings"]:
            page.refresh()

    def cleanup_status_changed(self, status: str):
        self.window.page_by_key["home"].set_cleanup_status(status)

    def quit(self):
        self.engine.shutdown()
        self.tray.hide()
        self.qapp.quit()


def main():
    _setup_logging()
    winintegration.set_app_id()
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("Murmur")
    qapp.setQuitOnLastWindowClosed(False)
    if _signal_running_instance():
        return
    from .ui import theme
    from .ui.icons import logo_icon

    theme.load_fonts()
    qapp.setStyle("Fusion")
    qapp.setStyleSheet(theme.STYLESHEET)
    qapp.setWindowIcon(logo_icon())
    app = MurmurApp(qapp, minimized="--minimized" in sys.argv)  # noqa: F841 (keeps everything alive)
    sys.exit(qapp.exec())
