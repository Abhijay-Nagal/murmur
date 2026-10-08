"""Microphone capture. The stream stays open so recording starts instantly, and a short
pre-roll buffer keeps the audio from just before the hotkey went down."""
import collections
import logging
import threading
from typing import Callable

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # what Whisper expects
BLOCK_SECONDS = 0.05
PREROLL_SECONDS = 0.3


def list_microphones() -> list[str]:
    """Input device names, deduplicated. Uses the MME host API, which lists every mic once
    with a friendly name and resamples to 16 kHz for us."""
    names = []
    try:
        mme = next(i for i, h in enumerate(sd.query_hostapis()) if h["name"] == "MME")
    except (StopIteration, sd.PortAudioError):
        mme = None
    for dev in sd.query_devices():
        if dev["max_input_channels"] > 0 and (mme is None or dev["hostapi"] == mme):
            name = dev["name"]
            if "Sound Mapper" not in name and name not in names:
                names.append(name)
    return names


def _find_device(name: str):
    if not name:
        return None
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and dev["name"] == name:
            return i
    log.warning("Microphone %r not found, using the default", name)
    return None


class Recorder:
    def __init__(self, device_name: str = "", on_level: Callable[[float], None] | None = None):
        self._lock = threading.Lock()
        self._recording = False
        self._chunks: list[np.ndarray] = []
        self.on_level = on_level
        device = _find_device(device_name)
        try:
            self._rate = SAMPLE_RATE
            self._stream = self._open(device)
        except sd.PortAudioError:
            # Some mics refuse 16 kHz; record at their native rate and resample on stop().
            self._rate = int(sd.query_devices(device, "input")["default_samplerate"])
            log.info("Mic does not support 16 kHz, recording at %d Hz", self._rate)
            self._stream = self._open(device)
        blocks = max(1, round(PREROLL_SECONDS / BLOCK_SECONDS))
        self._preroll: collections.deque[np.ndarray] = collections.deque(maxlen=blocks)

    def _open(self, device):
        return sd.InputStream(
            samplerate=self._rate,
            channels=1,
            dtype="float32",
            blocksize=int(self._rate * BLOCK_SECONDS),
            device=device,
            callback=self._callback,
        )

    def _callback(self, indata, frames, time_info, status):
        chunk = indata[:, 0].copy()
        with self._lock:
            if self._recording:
                self._chunks.append(chunk)
            else:
                self._preroll.append(chunk)
        if self.on_level:
            # Perceptual-ish 0..1 level for meters: RMS mapped from -60..0 dBFS.
            rms = float(np.sqrt(np.mean(chunk**2))) + 1e-9
            self.on_level(min(1.0, max(0.0, (20 * np.log10(rms) + 60) / 60)))

    @property
    def is_recording(self) -> bool:
        return self._recording

    def open(self):
        self._stream.start()

    def close(self):
        try:
            self._stream.stop()
            self._stream.close()
        except sd.PortAudioError:
            pass

    def start(self):
        with self._lock:
            self._chunks = list(self._preroll)
            self._preroll.clear()
            self._recording = True

    def stop(self) -> np.ndarray:
        """Stop recording and return mono float32 audio at 16 kHz."""
        with self._lock:
            self._recording = False
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(chunks)
        if self._rate != SAMPLE_RATE:
            n = int(len(audio) * SAMPLE_RATE / self._rate)
            audio = np.interp(
                np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio
            ).astype(np.float32)
        return audio
