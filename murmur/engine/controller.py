"""The dictation engine: mic -> Whisper -> cleanup -> paste, driven by the hotkey.

All heavy work runs on one worker thread, so dictations and model reloads never overlap.
The UI talks to it only through Qt signals and apply_settings().
"""
import logging
import queue
import threading
import time
import wave
from datetime import datetime

import numpy as np
from PySide6.QtCore import QObject, Signal

from ..paths import RECORDINGS_DIR
from ..settings import MODELS, Settings
from ..storage import Storage
from . import paster, sounds
from .cleanup import Cleaner
from .hotkey import Hotkey
from .recorder import SAMPLE_RATE, Recorder
from .text import apply_replacements, apply_voice_commands

log = logging.getLogger(__name__)


class Engine(QObject):
    # state: loading | ready | recording | hands_free | processing | paused | error
    state_changed = Signal(str, str)
    level = Signal(float)
    dictated = Signal(object)  # storage.Dictation
    notice = Signal(str)

    def __init__(self, settings: Settings, storage: Storage):
        super().__init__()
        self.s = settings
        self.storage = storage
        self.state = "loading"
        self.device = ""
        self.paused = False
        self.recorder: Recorder | None = None
        self.transcriber = None
        self.hotkey: Hotkey | None = None
        self.cleaner = Cleaner(settings.ollama_url, settings.ollama_model)
        self._jobs: queue.Queue = queue.Queue()
        self._app = ""
        self._limit_timer: threading.Timer | None = None

    # ---------- lifecycle ----------
    def start(self):
        threading.Thread(target=self._worker, daemon=True, name="murmur-engine").start()

    def shutdown(self):
        if self.hotkey:
            self.hotkey.stop()
        if self.recorder:
            self.recorder.close()
        self._jobs.put(None)

    def _worker(self):
        try:
            self._open_mic()
            self._configure_cleaner()
            if self.s.cleanup_enabled:
                threading.Thread(target=self.cleaner.warmup, daemon=True).start()
            self._load_model()
            self._start_hotkey()
        except Exception as e:
            log.exception("Startup failed")
            self._set_state("error", str(e))
            return
        self._idle()
        while (job := self._jobs.get()) is not None:
            kind, payload = job
            try:
                if kind == "reload":
                    self._load_model()
                elif kind == "audio":
                    self._process(*payload)
            except Exception as e:
                log.exception("Engine job %s failed", kind)
                self.notice.emit(f"Something went wrong: {e}")
            if not (self.recorder and self.recorder.is_recording):
                self._idle()

    # ---------- setup pieces ----------
    def _set_state(self, state: str, detail: str = ""):
        self.state = state
        self.state_changed.emit(state, detail)

    def _idle(self):
        self._set_state("paused" if self.paused else "ready")

    def _open_mic(self):
        if self.recorder:
            self.recorder.close()
        self.recorder = Recorder(self.s.mic_device, on_level=self.level.emit)
        self.recorder.open()

    def _configure_cleaner(self):
        c = self.cleaner
        c.base = self.s.ollama_url.rstrip("/").replace("localhost", "127.0.0.1")
        c.model = self.s.ollama_model
        c.enabled = self.s.cleanup_enabled
        c.style = self.s.cleanup_style
        c.vocabulary = list(self.s.vocabulary)

    def _load_model(self):
        from .transcriber import Transcriber  # heavy import (CUDA), keep off the UI thread

        label = MODELS.get(self.s.model, (self.s.model,))[0]
        self._set_state("loading", f"Loading the {label} speech model…")
        t0 = time.perf_counter()
        old, self.transcriber = self.transcriber, None
        del old  # free VRAM before loading the replacement
        tr = Transcriber(self.s.model, self.s.device)
        tr.language = self.s.language
        tr.vocabulary = list(self.s.vocabulary)
        self.transcriber, self.device = tr, tr.device
        log.info("Whisper %s ready on %s in %.1fs", self.s.model, tr.device, time.perf_counter() - t0)

    def _start_hotkey(self):
        if self.hotkey:
            self.hotkey.stop()
        self.hotkey = Hotkey(
            self.s.hotkey,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_cancel=self._on_cancel,
            min_hold=self.s.min_hold_seconds,
            hands_free=self.s.hands_free,
        )
        self.hotkey.paused = self.paused
        self.hotkey.start()

    # ---------- called from the UI thread ----------
    def apply_settings(self, new: Settings):
        old, self.s = self.s, new
        if self.transcriber:
            self.transcriber.language = new.language
            self.transcriber.vocabulary = list(new.vocabulary)
        self._configure_cleaner()
        if self.state == "loading" and not self.transcriber:
            return  # still starting up; the worker will pick up the new settings
        if (old.hotkey, old.hands_free, old.min_hold_seconds) != (new.hotkey, new.hands_free, new.min_hold_seconds):
            self._start_hotkey()
        if old.mic_device != new.mic_device:
            try:
                self._open_mic()
            except Exception as e:
                log.exception("Could not open microphone")
                self.notice.emit(f"Could not open that microphone: {e}")
        if (old.model, old.device) != (new.model, new.device):
            self._jobs.put(("reload", None))
        if new.cleanup_enabled and not old.cleanup_enabled:
            threading.Thread(target=self.cleaner.warmup, daemon=True).start()

    def set_paused(self, paused: bool):
        self.paused = paused
        if self.hotkey:
            self.hotkey.paused = paused
            self.hotkey.reset()
        if self.state in ("ready", "paused"):
            self._idle()

    # ---------- hotkey callbacks (keyboard hook thread: keep these fast) ----------
    def _on_start(self, hands_free: bool):
        if not self.transcriber or self.state == "loading":
            self.hotkey.reset()
            self.notice.emit("Still loading the speech model, one moment…")
            return
        self._app = paster.foreground_app()
        self.recorder.start()
        self._set_state("hands_free" if hands_free else "recording")
        if self.s.sounds:
            sounds.play("lock" if hands_free else "start")
        self._limit_timer = threading.Timer(self.s.max_recording_seconds, self._on_limit)
        self._limit_timer.daemon = True
        self._limit_timer.start()

    def _on_limit(self):
        if self.recorder.is_recording:
            self.hotkey.reset()
            self.notice.emit("Reached the maximum recording length")
            self._on_stop()

    def _cancel_limit(self):
        if self._limit_timer:
            self._limit_timer.cancel()
            self._limit_timer = None

    def _on_stop(self):
        self._cancel_limit()
        if not self.recorder.is_recording:
            return
        audio = self.recorder.stop()
        self._set_state("processing")
        if self.s.sounds:
            sounds.play("stop")
        self._jobs.put(("audio", (audio, self._app)))

    def _on_cancel(self):
        self._cancel_limit()
        if self.recorder.is_recording:
            self.recorder.stop()
        self._idle()

    # ---------- the pipeline (worker thread) ----------
    def _process(self, audio: np.ndarray, app: str):
        seconds = len(audio) / SAMPLE_RATE
        t0 = time.perf_counter()
        raw = self.transcriber.transcribe(audio)
        t1 = time.perf_counter()
        self._save_recording(audio)
        if not raw:
            log.info("Nothing heard (%.1fs audio)", seconds)
            self.notice.emit("Didn't catch that. Try speaking a little louder")
            if self.s.sounds:
                sounds.play("error")
            return
        text = apply_voice_commands(raw) if self.s.voice_commands else raw
        text, used_llm = self.cleaner.clean(text)
        text = apply_replacements(text, self.s.replacements)
        t2 = time.perf_counter()
        paster.paste(text + (" " if self.s.trailing_space and not text.endswith("\n") else ""),
                     self.s.restore_clipboard)
        log.info("%.1fs audio | whisper %.2fs | cleanup %.2fs%s | into %s",
                 seconds, t1 - t0, t2 - t1, "" if used_llm else " (rules)", app or "?")
        if self.s.save_history:
            self.dictated.emit(self.storage.add(raw, text, app, seconds))

    def _save_recording(self, audio: np.ndarray):
        keep = self.s.keep_recordings
        if keep <= 0 or not len(audio):
            return
        RECORDINGS_DIR.mkdir(exist_ok=True)
        with wave.open(str(RECORDINGS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        for old in sorted(RECORDINGS_DIR.glob("*.wav"))[:-keep]:
            old.unlink(missing_ok=True)
