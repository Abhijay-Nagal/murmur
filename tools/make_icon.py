"""Render the Murmur logo to assets/murmur.png and a multi-size assets/murmur.ico."""
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from murmur.paths import ICON_ICO, ICON_PNG  # noqa: E402
from murmur.ui.icons import logo_pixmap  # noqa: E402

app = QApplication([])
ICON_PNG.parent.mkdir(exist_ok=True)
logo_pixmap(256).save(str(ICON_PNG))
Image.open(ICON_PNG).save(ICON_ICO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote", ICON_PNG, ICON_ICO)
