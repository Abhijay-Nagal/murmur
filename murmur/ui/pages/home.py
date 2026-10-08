from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import theme
from ..icons import icon
from ..widgets import Badge, Card, Keycap, Page, StatCell, clear_layout, label

STATE_TEXT = {
    "loading": "Starting up",
    "ready": "Ready",
    "recording": "Listening",
    "hands_free": "Listening (hands-free)",
    "processing": "Transcribing",
    "paused": "Paused",
    "error": "Error",
}


def _greeting() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


def _fmt_int(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


class HomePage(Page):
    open_page = Signal(str)

    def __init__(self, app):
        super().__init__(_greeting(), "Speak anywhere you can type. Murmur runs entirely on this computer.")
        self.app = app

        # ---- hero: how to dictate ----
        hero = Card("HeroCard", padding=28, spacing=14)
        top = QHBoxLayout()
        top.addWidget(label("Hold to dictate", "HeroTitle"))
        top.addStretch(1)
        self.status = Badge("Starting up", theme.MUTED)
        top.addWidget(self.status)
        hero.body.addLayout(top)
        self.keys_row = QHBoxLayout()
        self.keys_row.setSpacing(8)
        hero.body.addLayout(self.keys_row)
        self.hint = label("", "Muted", wrap=True)
        hero.body.addWidget(self.hint)
        self.body.addWidget(hero)

        # ---- setup nudge (AI cleanup) ----
        self.nudge = Card(padding=16, spacing=8)
        n_ico = QLabel()
        n_ico.setPixmap(icon("sparkles", theme.WARNING, 18).pixmap(18, 18))
        self.nudge_text = label("", wrap=True)
        go = QPushButton("Set up")
        go.setObjectName("Primary")
        go.setCursor(Qt.PointingHandCursor)
        go.clicked.connect(lambda: self.open_page.emit("settings"))
        go.setFocusPolicy(Qt.NoFocus)
        nudge_row = QHBoxLayout()
        nudge_row.setSpacing(12)
        nudge_row.addWidget(n_ico, 0, Qt.AlignVCenter)
        nudge_row.addWidget(self.nudge_text, 1)
        nudge_row.addWidget(go, 0, Qt.AlignVCenter)
        self.nudge.body.addLayout(nudge_row)
        self.nudge.hide()
        self.body.addWidget(self.nudge)

        # ---- stats: one ledger row ----
        ledger = Card(padding=22, spacing=0)
        row = QHBoxLayout()
        row.setSpacing(0)
        self.s_today = StatCell("Words today", first=True)
        self.s_total = StatCell("Total words")
        self.s_wpm = StatCell("Speaking speed")
        self.s_saved = StatCell("Time saved")
        for c in (self.s_today, self.s_total, self.s_wpm, self.s_saved):
            row.addWidget(c, 1)
        ledger.body.addLayout(row)
        self.body.addWidget(ledger)

        # ---- recent ----
        recent = Card(padding=22, spacing=6)
        head = QHBoxLayout()
        head.addWidget(label("Lately", "CardTitle"))
        head.addStretch(1)
        see_all = QPushButton("See all →")
        see_all.setObjectName("Link")
        see_all.setCursor(Qt.PointingHandCursor)
        see_all.clicked.connect(lambda: self.open_page.emit("history"))
        head.addWidget(see_all)
        recent.body.addLayout(head)
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(0)
        recent.body.addLayout(self.recent_box)
        self.body.addWidget(recent)
        self.finish()

        self.refresh()

    def set_state(self, state: str, detail: str):
        text = STATE_TEXT.get(state, state)
        if state == "ready" and self.app.engine.device:
            text = f"Ready · {'GPU' if self.app.engine.device == 'cuda' else 'CPU'}"
        if state == "loading" and detail:
            text = detail
        self.status.set(text, theme.STATE_COLORS.get(state, theme.MUTED))

    def set_cleanup_status(self, status: str):
        if not self.app.settings.cleanup_enabled or status == "ready":
            self.nudge.hide()
            return
        self.nudge_text.setText(
            "<b>Turn on AI cleanup.</b> Removes “um”s, handles “no wait, I meant…” and formats lists, "
            "like Wispr Flow. Free and offline; it takes about 2 minutes to set up."
            if status == "not_running" else
            "<b>One more step for AI cleanup:</b> download the small cleanup model (about 2 GB)."
        )
        self.nudge.show()

    def refresh(self):
        s = self.app.settings
        clear_layout(self.keys_row)
        for i, part in enumerate(s.hotkey_label.split(" + ")):
            if i:
                self.keys_row.addWidget(label("+", "Muted"))
            self.keys_row.addWidget(Keycap(part))
        self.keys_row.addStretch(1)
        hint = "Hold the keys, speak, then let go. Your words appear wherever the cursor is."
        if s.hands_free:
            hint += " Double-tap the keys for hands-free mode, then tap once to finish."
        self.hint.setText(hint)

        st = self.app.storage.stats()
        self.s_today.value.setText(_fmt_int(st.words_today))
        self.s_today.hint.setText(f"{st.streak_days}-day streak" if st.streak_days > 1 else "Keep talking")
        self.s_total.value.setText(_fmt_int(st.words_total))
        self.s_total.hint.setText(f"{st.dictations_total:,} dictations")
        self.s_wpm.value.setText(f"{st.avg_wpm:.0f} wpm" if st.avg_wpm else "—")
        self.s_wpm.hint.setText("vs ~40 wpm typing")
        mins = st.minutes_saved
        self.s_saved.value.setText(f"{mins / 60:.1f} h" if mins >= 90 else f"{mins:.0f} min")
        self.s_saved.hint.setText("compared with typing")

        clear_layout(self.recent_box)
        items = self.app.storage.recent(5)
        if not items:
            empty = label("Nothing yet. Hold the hotkey and say something to try it.", "Muted")
            empty.setContentsMargins(0, 10, 0, 6)
            self.recent_box.addWidget(empty)
        for d in items:
            row = QWidget()
            row.setObjectName("Row")
            row.setAttribute(Qt.WA_StyledBackground, True)
            lay = QVBoxLayout(row)
            lay.setContentsMargins(0, 12, 0, 12)
            lay.setSpacing(3)
            meta = d.ts.strftime("%I:%M %p").lstrip("0") + (f"  ·  {d.app}" if d.app else "")
            lay.addWidget(label(meta, "Faint"))
            text = d.final if len(d.final) < 220 else d.final[:217] + "…"
            lay.addWidget(label(text, wrap=True))
            self.recent_box.addWidget(row)
