import os
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ... import __version__
from ...paths import DATA_DIR
from .. import theme
from ..icons import icon, logo_pixmap
from ..widgets import Card, Page, SettingsCard, label

REPO_URL = "https://github.com/Abhijay-Nagal/murmur"


class AboutPage(Page):
    def __init__(self, app):
        super().__init__("About")
        self.app = app

        hero = Card("HeroCard", padding=28, spacing=10)
        row = QHBoxLayout()
        row.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(72))
        row.addWidget(logo)
        txt = QVBoxLayout()
        txt.setSpacing(4)
        txt.addWidget(label("Murmur", "PageTitle"))
        txt.addWidget(label("made by Abhijay Nagal", "BrandTag"))
        txt.addWidget(label(f"Version {__version__}  ·  Free, offline voice dictation for Windows", "Muted"))
        row.addLayout(txt, 1)
        hero.body.addLayout(row)
        self.body.addWidget(hero)

        priv = SettingsCard("Private by design", "shield")
        for line in (
            "Speech recognition runs on your own graphics card with OpenAI's open-source Whisper model.",
            "AI cleanup runs locally through Ollama. Nothing you say is ever sent to a server.",
            "No account, no subscription, no word limits.",
        ):
            r = QHBoxLayout()
            r.setSpacing(10)
            ic = QLabel()
            ic.setPixmap(icon("check", theme.SUCCESS, 15).pixmap(15, 15))
            r.addWidget(ic, 0, Qt.AlignTop)
            r.addWidget(label(line, wrap=True), 1)
            priv.body.addLayout(r)
            priv.body.addSpacing(6)
        self.body.addWidget(priv)

        sysc = SettingsCard("System", "cpu")
        self.engine_lbl = label("", "Muted")
        sysc.add("Speech engine", "", self.engine_lbl)
        folder = QPushButton("  Open folder")
        folder.setIcon(icon("folder", theme.TEXT, 15))
        folder.clicked.connect(lambda: os.startfile(DATA_DIR))
        sysc.add("Your data", str(DATA_DIR), folder)
        self.body.addWidget(sysc)

        credits = SettingsCard("Built with", "sparkles")
        credits.body.addWidget(label(
            "faster-whisper and CTranslate2 · OpenAI Whisper · Silero VAD · Ollama and Qwen 2.5 · Qt for Python (PySide6)",
            "Muted", wrap=True))
        gh = QPushButton("  View on GitHub")
        gh.setIcon(icon("github", theme.TEXT, 15))
        gh.clicked.connect(lambda: webbrowser.open(REPO_URL))
        credits.body.addSpacing(10)
        credits.body.addWidget(gh, 0, Qt.AlignLeft)
        self.body.addWidget(credits)
        self.finish()

    def refresh(self):
        e = self.app.engine
        dev = {"cuda": "NVIDIA GPU (CUDA)", "cpu": "CPU"}.get(e.device, "loading…")
        self.engine_lbl.setText(f"{self.app.settings.model} on {dev}")
