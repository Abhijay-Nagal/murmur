"""Short, soft UI sounds, synthesized once at import (no audio files to ship)."""
import io
import threading
import wave
import winsound

import numpy as np

_RATE = 44100


def _tone(freqs: list[float], note_ms: int = 70, volume: float = 0.18) -> bytes:
    notes = []
    for f in freqs:
        t = np.arange(int(_RATE * note_ms / 1000)) / _RATE
        wave_ = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)  # soft overtone
        env = np.minimum(1, t / 0.006) * np.exp(-t * 28)  # quick attack, gentle decay
        notes.append(wave_ * env)
    samples = (np.concatenate(notes) / 1.3 * volume * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


_SOUNDS = {
    "start": _tone([660, 990]),
    "lock": _tone([660, 880, 1100]),
    "stop": _tone([880, 587]),
    "error": _tone([330, 262], note_ms=110),
}


def play(name: str):
    # SND_MEMORY can't be combined with SND_ASYNC, so play on a short-lived thread.
    threading.Thread(
        target=winsound.PlaySound, args=(_SOUNDS[name], winsound.SND_MEMORY), daemon=True
    ).start()
