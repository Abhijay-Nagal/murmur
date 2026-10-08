"""Called by install.bat: picks the right speech model for this PC and downloads it.

    python tools/install_helper.py gpu   -> Turbo model on the NVIDIA GPU
    python tools/install_helper.py cpu   -> Small model on the processor (no NVIDIA GPU found)

Existing settings are never overwritten, so re-running the installer keeps your choices.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from murmur.paths import SETTINGS_PATH  # noqa: E402
from murmur.settings import Settings  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "gpu"
if SETTINGS_PATH.exists():
    settings = Settings.load()
else:
    settings = Settings()
    if mode == "cpu":
        settings.model, settings.device = "small.en", "cpu"
    settings.save()

print(f"Downloading the speech model ({settings.model}). This happens once.")
from faster_whisper.utils import download_model  # noqa: E402

download_model(settings.model)
print("Speech model ready.")
