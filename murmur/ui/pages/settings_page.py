import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QProgressBar, QPushButton, QSpinBox, QWidget

from ... import winintegration
from ...engine.recorder import list_microphones
from ...settings import CLEANUP_STYLES, HOTKEY_PRESETS, LANGUAGES, MODELS
from .. import theme
from ..tasks import run_async
from ..widgets import Badge, LevelMeter, Page, SettingsCard, Toggle, hbox, label

OLLAMA_DOWNLOAD = "https://ollama.com/download"


def _combo(items: dict, current) -> QComboBox:
    c = QComboBox()
    c.setMinimumWidth(220)
    c.setCursor(Qt.PointingHandCursor)
    for value, text in items.items():
        c.addItem(text, value)
    i = c.findData(current)
    c.setCurrentIndex(max(0, i))
    return c


class SettingsPage(Page):
    def __init__(self, app):
        super().__init__("Settings", "Changes apply instantly.")
        self.app = app
        s = app.settings

        # ---------------- Dictation ----------------
        dic = SettingsCard("Dictation", "mic")
        hotkeys = {label_: label_ for label_ in HOTKEY_PRESETS}
        self.hotkey = dic.add("Push-to-talk keys", "Hold these keys while you speak.",
                              _combo(hotkeys, s.hotkey_label))
        self.hotkey.currentIndexChanged.connect(
            lambda: self._set("hotkey", HOTKEY_PRESETS[self.hotkey.currentData()]))
        self._toggle(dic, "hands_free", "Hands-free mode",
                     "Double-tap the keys to keep recording without holding them. Tap once to finish, or press Esc to cancel.")
        self.language = dic.add("Language", "English is fastest and most accurate. Auto-detect handles several languages.",
                                _combo(LANGUAGES, s.language))
        self.language.currentIndexChanged.connect(lambda: self._set("language", self.language.currentData()))
        self._toggle(dic, "voice_commands", "Voice commands", "Say “new line” or “new paragraph” to format as you speak.")
        self._toggle(dic, "trailing_space", "Add a space after each dictation",
                     "So consecutive dictations don't run together.")
        self._toggle(dic, "restore_clipboard", "Restore clipboard",
                     "Murmur pastes through the clipboard, then puts back what you had copied.")
        mx = QSpinBox()
        mx.setRange(1, 30)
        mx.setSuffix(" min")
        mx.setValue(max(1, s.max_recording_seconds // 60))
        mx.valueChanged.connect(lambda v: self._set("max_recording_seconds", v * 60))
        dic.add("Maximum recording length", "Recording stops automatically after this long.", mx)
        self.body.addWidget(dic)

        # ---------------- Microphone ----------------
        mic = SettingsCard("Microphone", "mic")
        mics = {"": "Windows default"} | {m: m for m in list_microphones()}
        self.mic = mic.add("Input device", "Pick the mic you speak into.", _combo(mics, s.mic_device))
        self.mic.setMinimumWidth(280)
        self.mic.currentIndexChanged.connect(lambda: self._set("mic_device", self.mic.currentData()))
        self.meter = LevelMeter()
        self.meter.setFixedWidth(280)
        mic.add("Input level", "Speak normally. The bars should reach the middle.", self.meter)
        self.body.addWidget(mic)

        # ---------------- Speech model ----------------
        mod = SettingsCard("Speech recognition", "cpu",
                           "Runs on your graphics card with Whisper. A new model downloads once when you pick it.")
        models = {k: f"{v[0]}  ·  {v[2]}" for k, v in MODELS.items()}
        self.model = mod.add("Model", "", _combo(models, s.model))
        self.model_desc = mod.last_row.desc
        self.model.currentIndexChanged.connect(self._model_changed)
        self._update_model_desc()
        self.device = mod.add("Processor", "Auto uses your NVIDIA GPU when available.",
                              _combo({"auto": "Auto", "cuda": "GPU (CUDA)", "cpu": "CPU"}, s.device))
        self.device.currentIndexChanged.connect(lambda: self._set("device", self.device.currentData()))
        self.body.addWidget(mod)

        # ---------------- AI cleanup ----------------
        ai = SettingsCard("AI cleanup", "sparkles",
                          "A small AI model on your computer removes filler words, applies self-corrections "
                          "(“Tuesday, no wait, Wednesday”) and formats lists, like Wispr Flow. "
                          "Free and offline, powered by Ollama.")
        self._toggle(ai, "cleanup_enabled", "Enable AI cleanup", "When off, Murmur only removes “um” and “uh”.")
        styles = {k: v[0] for k, v in CLEANUP_STYLES.items()}
        self.style = ai.add("Style", CLEANUP_STYLES.get(s.cleanup_style, CLEANUP_STYLES["light"])[1],
                            _combo(styles, s.cleanup_style))
        self.style_desc = ai.last_row.desc
        self.style.currentIndexChanged.connect(self._style_changed)

        status_box = QWidget()
        sb = QHBoxLayout(status_box)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(8)
        self.ollama_badge = Badge("Checking…", theme.MUTED)
        self.ollama_btn = QPushButton("Check again")
        self.ollama_btn.setCursor(Qt.PointingHandCursor)
        self.ollama_btn.clicked.connect(self._ollama_action)
        sb.addWidget(self.ollama_badge)
        sb.addWidget(self.ollama_btn)
        self.ollama_row = ai.add("Status", "Checking whether Ollama is running…", status_box)
        self.ollama_desc = ai.last_row.desc
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.hide()
        self.progress_lbl = label("", "Faint")
        self.progress_lbl.hide()
        ai.add_widget(self.progress)
        ai.add_widget(self.progress_lbl)
        self.ollama_state = "unknown"
        self.body.addWidget(ai)

        # ---------------- App ----------------
        gen = SettingsCard("App", "settings")
        start = gen.add("Start with Windows", "Murmur starts quietly in the tray when you log in.",
                        Toggle(s.start_with_windows))
        start.toggled.connect(self._start_with_windows)
        sc = QPushButton("Create shortcuts")
        sc.setCursor(Qt.PointingHandCursor)
        sc.clicked.connect(self._shortcuts)
        self.sc_btn = gen.add("Desktop & Start Menu", "Add a Murmur icon to your desktop and Start Menu.", sc)
        self._toggle(gen, "sounds", "Sounds", "A soft chime when recording starts and stops.")
        self._toggle(gen, "overlay", "Recording indicator", "A floating bar with a live waveform while you speak.")
        self._toggle(gen, "save_history", "Save history", "Keep a searchable history of your dictations on this computer.")
        rec = QSpinBox()
        rec.setRange(0, 500)
        rec.setValue(s.keep_recordings)
        rec.setSpecialValueText("Off")
        rec.valueChanged.connect(lambda v: self._set("keep_recordings", v))
        gen.add("Keep audio recordings", "The last N recordings, saved for troubleshooting accuracy.", rec)
        self.body.addWidget(gen)
        self.finish()

    # ---------- helpers ----------
    def _toggle(self, card, attr, title, desc):
        t = Toggle(getattr(self.app.settings, attr))
        t.toggled.connect(lambda v: self._set(attr, v))
        card.add(title, desc, t)
        return t

    def _set(self, attr, value):
        s = self.app.settings.copy()
        setattr(s, attr, value)
        self.app.update_settings(s)
        if attr == "cleanup_enabled":
            self.check_ollama()

    def push_level(self, v: float):
        if self.isVisible():
            self.meter.set_level(v)

    def _update_model_desc(self):
        self.model_desc.setText(MODELS[self.model.currentData()][1])
        self.model_desc.show()

    def _model_changed(self):
        self._update_model_desc()
        self._set("model", self.model.currentData())

    def _style_changed(self):
        self.style_desc.setText(CLEANUP_STYLES[self.style.currentData()][1])
        self._set("cleanup_style", self.style.currentData())

    def _start_with_windows(self, on: bool):
        try:
            winintegration.set_start_with_windows(on)
            self._set("start_with_windows", on)
        except Exception as e:
            self.app.notify(f"Couldn't change startup setting: {e}")

    def _shortcuts(self):
        self.sc_btn.setEnabled(False)
        self.sc_btn.setText("Creating…")

        def done(_):
            self.sc_btn.setText("Created ✓")
            self.sc_btn.setEnabled(True)

        def fail(msg):
            self.sc_btn.setText("Create shortcuts")
            self.sc_btn.setEnabled(True)
            self.app.notify(f"Couldn't create shortcuts: {msg}")

        run_async(winintegration.create_desktop_and_start_menu, done, fail)

    # ---------- Ollama ----------
    def check_ollama(self):
        self.ollama_badge.set("Checking…", theme.MUTED)
        run_async(self.app.engine.cleaner.status, self._show_ollama)

    def _show_ollama(self, status: str):
        self.ollama_state = status
        self.app.cleanup_status_changed(status)
        if status == "ready":
            self.ollama_badge.set("Ready", theme.SUCCESS)
            self.ollama_desc.setText(f"Using {self.app.settings.ollama_model} through Ollama.")
            self.ollama_btn.setText("Check again")
        elif status == "model_missing":
            self.ollama_badge.set("Model needed", theme.WARNING)
            self.ollama_desc.setText(
                f"Ollama is running. Download the cleanup model ({self.app.settings.ollama_model}, about 2 GB).")
            self.ollama_btn.setText("Download model")
        else:
            self.ollama_badge.set("Not installed", theme.DANGER)
            self.ollama_desc.setText(
                "Install Ollama (free), then click Check again. If it's installed, start it from the Start Menu.")
            self.ollama_btn.setText("Get Ollama")
        self.ollama_btn.setObjectName("Primary" if status != "ready" else "")
        self.ollama_btn.style().unpolish(self.ollama_btn)
        self.ollama_btn.style().polish(self.ollama_btn)

    def _ollama_action(self):
        if self.ollama_state == "not_running":
            webbrowser.open(OLLAMA_DOWNLOAD)
            self.ollama_btn.setText("Check again")
            self.ollama_state = "waiting"
        elif self.ollama_state == "model_missing":
            self._pull()
        else:
            self.check_ollama()

    def _pull(self):
        self.ollama_btn.setEnabled(False)
        self.progress.show()
        self.progress_lbl.show()
        self.progress.setValue(0)

        def progress(frac, msg):
            if frac >= 0:
                self.progress.setValue(int(frac * 1000))
                self.progress_lbl.setText(f"Downloading… {frac * 100:.0f}%")
            else:
                self.progress_lbl.setText(msg.capitalize())

        def finished(_):
            self.progress.hide()
            self.progress_lbl.hide()
            self.ollama_btn.setEnabled(True)
            self.check_ollama()
            run_async(self.app.engine.cleaner.warmup)

        def failed(msg):
            self.progress.hide()
            self.progress_lbl.setText(f"Download failed: {msg}")
            self.ollama_btn.setEnabled(True)

        run_async(self.app.engine.cleaner.pull, finished, failed, progress)
