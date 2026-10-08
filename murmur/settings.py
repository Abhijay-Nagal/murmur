"""User settings, stored as JSON. Unknown keys are ignored and missing ones get defaults,
so old settings files keep working as new options are added."""
import json
import logging
from dataclasses import asdict, dataclass, field, fields

from .paths import SETTINGS_PATH

log = logging.getLogger(__name__)

HOTKEY_PRESETS = {
    "Ctrl + Alt": ["ctrl", "alt"],
    "Ctrl + Win": ["ctrl", "windows"],
    "Ctrl + Shift": ["ctrl", "shift"],
    "Alt + Shift": ["alt", "shift"],
    "Right Ctrl": ["right ctrl"],
}

MODELS = {
    "large-v3-turbo": ("Turbo", "Fast and accurate. Recommended", "1.6 GB"),
    "large-v3": ("Large v3", "Most accurate, about 2x slower", "3 GB"),
    "distil-large-v3": ("Distil", "Fastest large model, English only", "1.5 GB"),
    "small.en": ("Small", "For computers without a GPU", "0.5 GB"),
}

LANGUAGES = {
    "en": "English",
    "auto": "Auto-detect",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
}

CLEANUP_STYLES = {
    "light": ("Light", "Removes fillers and fixes punctuation. Keeps your exact words."),
    "polished": ("Polished", "Also fixes grammar and smooths awkward phrasing."),
    "casual": ("Casual", "Relaxed chat style, for messages to friends."),
}


@dataclass
class Settings:
    # Dictation
    hotkey: list[str] = field(default_factory=lambda: ["ctrl", "alt"])
    hands_free: bool = True  # double-tap the hotkey to record without holding
    min_hold_seconds: float = 0.3
    max_recording_seconds: int = 300
    language: str = "en"
    voice_commands: bool = True
    trailing_space: bool = True
    restore_clipboard: bool = True

    # Microphone
    mic_device: str = ""  # empty = Windows default

    # Speech model
    model: str = "large-v3-turbo"
    device: str = "auto"  # auto | cuda | cpu

    # AI cleanup
    cleanup_enabled: bool = True
    cleanup_style: str = "light"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"

    # Words
    vocabulary: list[str] = field(default_factory=lambda: [
        "Claude", "Gemini", "ChatGPT", "Wispr Flow", "GitHub", "VS Code",
        "Python", "JavaScript", "React", "NumPy", "JEE",
    ])
    replacements: list[list[str]] = field(default_factory=list)  # [[spoken, typed], ...]

    # App
    sounds: bool = True
    overlay: bool = True
    save_history: bool = True
    keep_recordings: int = 20
    start_with_windows: bool = False

    @property
    def hotkey_label(self) -> str:
        for label, keys in HOTKEY_PRESETS.items():
            if keys == self.hotkey:
                return label
        return " + ".join(k.title() for k in self.hotkey)

    @classmethod
    def load(cls) -> "Settings":
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError):
            log.exception("Settings file unreadable, using defaults")
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self):
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_PATH)

    def copy(self) -> "Settings":
        return Settings(**json.loads(json.dumps(asdict(self))))
