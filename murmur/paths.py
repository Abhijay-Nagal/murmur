"""Where Murmur keeps its files. User data lives in %APPDATA%\\Murmur so it survives updates."""
import os
from pathlib import Path

APP_NAME = "Murmur"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICON_ICO = ASSETS / "murmur.ico"
ICON_PNG = ASSETS / "murmur.png"

DATA_DIR = Path(os.environ.get("MURMUR_DATA_DIR") or Path(os.environ.get("APPDATA", Path.home())) / APP_NAME)
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = DATA_DIR / "settings.json"
DB_PATH = DATA_DIR / "history.db"
LOG_PATH = DATA_DIR / "murmur.log"
RECORDINGS_DIR = DATA_DIR / "recordings"
