"""Speech to text with faster-whisper, kept loaded on the GPU between dictations.

Run directly to test: python -m murmur.engine.transcriber file.wav
"""
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000


def _add_nvidia_dll_dirs():
    """Make the pip-installed cuBLAS/cuDNN DLLs findable, so no system CUDA install is needed."""
    try:
        import nvidia
    except ImportError:
        return
    for base in nvidia.__path__:
        for lib in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
            bin_dir = Path(base) / lib / "bin"
            if bin_dir.is_dir():
                os.add_dll_directory(str(bin_dir))
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


_add_nvidia_dll_dirs()
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from faster_whisper import WhisperModel  # noqa: E402  (needs the DLL dirs above)
from faster_whisper.vad import VadOptions, get_speech_timestamps  # noqa: E402

# large-v3 in int8 weights keeps VRAM low enough to share the GPU with the cleanup LLM,
# with no measurable accuracy loss.
_CUDA_COMPUTE = {"large-v3": "int8_float16"}


class Transcriber:
    def __init__(self, model: str, device: str = "auto"):
        self.model_name = model
        self.model, self.device = self._load(model, device)
        self.language = "en"
        self.vocabulary: list[str] = []

    def _load(self, name: str, device: str):
        if device in ("auto", "cuda"):
            try:
                model = WhisperModel(name, device="cuda", compute_type=_CUDA_COMPUTE.get(name, "float16"))
                # cuDNN/cuBLAS load lazily, so only a real inference proves CUDA works.
                self._warmup(model)
                return model, "cuda"
            except Exception:
                log.exception("CUDA unavailable, falling back to CPU (much slower)")
        model = WhisperModel(name, device="cpu", compute_type="int8")
        self._warmup(model)
        return model, "cpu"

    @staticmethod
    def _warmup(model):
        segments, _ = model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language="en")
        list(segments)

    def transcribe(self, audio: np.ndarray) -> str:
        audio = prepare(audio)
        if audio is None:
            return ""  # no speech; Whisper hallucinates "Thank you." on silence
        long_form = len(audio) > SAMPLE_RATE * 30
        segments, _ = self.model.transcribe(
            audio,
            language=None if self.language == "auto" else self.language,
            beam_size=5,
            # Never cut inside a short dictation: the VAD drops soft or fast words in
            # push-to-talk clips. Long hands-free recordings do need pauses removed,
            # or Whisper hallucinates in the gaps, so only those get a lenient VAD.
            vad_filter=long_form,
            vad_parameters={"min_silence_duration_ms": 2000, "threshold": 0.3} if long_form else None,
            initial_prompt=", ".join(self.vocabulary) + "." if self.vocabulary else None,
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4],
        )
        return " ".join(s.text.strip() for s in segments).strip()


def prepare(audio: np.ndarray) -> np.ndarray | None:
    """Detect speech and trim only the leading/trailing silence.
    Returns None when there's no speech at all."""
    if len(audio) < SAMPLE_RATE * 0.3:
        return None
    # Lenient settings: the goal is only "did the user speak, and where does it start/end".
    speech = get_speech_timestamps(
        audio, VadOptions(threshold=0.3, min_silence_duration_ms=2000, speech_pad_ms=0)
    )
    if not speech:
        return None
    pad = int(SAMPLE_RATE * 0.5)
    start = max(0, speech[0]["start"] - pad)
    end = min(len(audio), speech[-1]["end"] + pad)
    return audio[start:end]


def read_wav(path: str) -> np.ndarray:
    """16-bit PCM WAV -> mono float32 at 16 kHz."""
    import wave

    with wave.open(path, "rb") as w:
        rate, channels = w.getframerate(), w.getnchannels()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    audio = pcm.reshape(-1, channels).mean(axis=1).astype(np.float32) / 32768
    if rate != SAMPLE_RATE:
        n = int(len(audio) * SAMPLE_RATE / rate)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio)
    return audio.astype(np.float32)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: python -m murmur.engine.transcriber <file.wav> [model]")
    t0 = time.perf_counter()
    tr = Transcriber(sys.argv[2] if len(sys.argv) == 3 else "large-v3-turbo")
    print(f"loaded on {tr.device} in {time.perf_counter() - t0:.1f}s")
    audio = read_wav(sys.argv[1])
    t0 = time.perf_counter()
    text = tr.transcribe(audio)
    print(f"{len(audio) / SAMPLE_RATE:.1f}s of audio transcribed in {time.perf_counter() - t0:.2f}s")
    print(text)
