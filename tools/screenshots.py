"""Render every page with sample data to docs/screenshots/ (for the README and design checks).

Uses a throwaway data folder, so your real history and settings are never touched.
"""
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["MURMUR_DATA_DIR"] = tempfile.mkdtemp(prefix="murmur-demo-")
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QEvent, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from murmur import app as app_mod  # noqa: E402
from murmur.settings import Settings  # noqa: E402
from murmur.storage import Storage  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

DEMO = [
    ("Chrome", "Can you send me the slides from today's lecture? I want to go through the derivations again before the quiz.", 6.2),
    ("VS Code", "Refactor this function so the cache is invalidated whenever the settings file changes.", 4.8),
    ("WhatsApp", "Running 10 minutes late, start without me. I'll grab the notes from Priya.", 3.9),
    ("Notion", "Plan for the week:\n1. Finish the physics mock test\n2. Revise organic chemistry\n3. Push the Murmur update to GitHub", 7.5),
    ("Slack", "The deploy is green. I'll keep an eye on the error rate for the next hour.", 4.1),
    ("Gmail", "Hi team, attaching the final report. Let me know if anything needs another pass before Friday.", 5.6),
]

s = Settings()
s.replacements = [["my email", "you@example.com"], ["sig", "Best regards,\nAlex"]]
s.save()
store = Storage()
for i, (app_name, text, secs) in enumerate(DEMO * 3):
    d = store.add(text, text, app_name, secs)
    ts = datetime.now() - timedelta(hours=i * 7)
    store._db.execute("UPDATE dictations SET ts=? WHERE id=?", (ts.isoformat(timespec="seconds"), d.id))
store._db.commit()

app_mod._setup_logging()
qapp = QApplication(sys.argv)
qapp.setQuitOnLastWindowClosed(False)
from murmur.ui import theme  # noqa: E402

theme.load_fonts()
qapp.setStyle("Fusion")
qapp.setStyleSheet(theme.STYLESHEET)
m = app_mod.MurmurApp(qapp, minimized=False)
m.window.resize(1100, 760)


def shoot():
    if m.engine.state == "loading":
        QTimer.singleShot(500, shoot)
        return
    for key in ("home", "history", "dictionary", "settings", "about"):
        m.window.show_page(key)
        for _ in range(20):
            qapp.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        if key == "settings":
            page = m.window.page_by_key["settings"]
            page.meter.set_level(0.55)
            page.scroll.widget().grab().save(str(OUT / "settings_full.png"))
        m.window.grab().save(str(OUT / f"{key}.png"))
    ov = m.overlay
    ov.show_state("recording")
    for i in range(22):
        ov.push_level(0.35 + 0.45 * abs(math.sin(i * 0.7)))
    ov.grab().save(str(OUT / "overlay.png"))
    ov.show_state("hands_free")
    ov.grab().save(str(OUT / "overlay_handsfree.png"))
    print("saved to", OUT)
    m.quit()


QTimer.singleShot(1000, shoot)
qapp.exec()
