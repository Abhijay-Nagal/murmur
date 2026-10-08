"""Dictation history and usage stats in a local SQLite database."""
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from .paths import DB_PATH

TYPING_WPM = 40  # average typing speed, used for "time saved"


@dataclass
class Dictation:
    id: int
    ts: datetime
    raw: str
    final: str
    app: str
    audio_seconds: float
    words: int


@dataclass
class Stats:
    words_today: int
    words_total: int
    dictations_total: int
    avg_wpm: float
    minutes_saved: float
    streak_days: int


class Storage:
    def __init__(self, path=DB_PATH):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS dictations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                raw TEXT NOT NULL,
                final TEXT NOT NULL,
                app TEXT NOT NULL DEFAULT '',
                audio_seconds REAL NOT NULL DEFAULT 0,
                words INTEGER NOT NULL DEFAULT 0
            )"""
        )
        self._db.commit()

    def add(self, raw: str, final: str, app: str, audio_seconds: float) -> Dictation:
        now = datetime.now()
        words = len(final.split())
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO dictations (ts, raw, final, app, audio_seconds, words) VALUES (?,?,?,?,?,?)",
                (now.isoformat(timespec="seconds"), raw, final, app, audio_seconds, words),
            )
            self._db.commit()
        return Dictation(cur.lastrowid, now, raw, final, app, audio_seconds, words)

    def recent(self, limit: int = 200, search: str = "") -> list[Dictation]:
        sql = "SELECT id, ts, raw, final, app, audio_seconds, words FROM dictations"
        args: tuple = ()
        if search:
            sql += " WHERE final LIKE ? OR app LIKE ?"
            args = (f"%{search}%", f"%{search}%")
        sql += " ORDER BY ts DESC, id DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(sql, args + (limit,)).fetchall()
        return [Dictation(r[0], datetime.fromisoformat(r[1]), *r[2:]) for r in rows]

    def delete(self, dictation_id: int):
        with self._lock:
            self._db.execute("DELETE FROM dictations WHERE id = ?", (dictation_id,))
            self._db.commit()

    def clear(self):
        with self._lock:
            self._db.execute("DELETE FROM dictations")
            self._db.commit()

    def stats(self) -> Stats:
        today = datetime.now().date().isoformat()
        with self._lock:
            total_words, total_secs, count = self._db.execute(
                "SELECT COALESCE(SUM(words),0), COALESCE(SUM(audio_seconds),0), COUNT(*) FROM dictations"
            ).fetchone()
            words_today = self._db.execute(
                "SELECT COALESCE(SUM(words),0) FROM dictations WHERE ts >= ?", (today,)
            ).fetchone()[0]
            days = {r[0] for r in self._db.execute("SELECT DISTINCT substr(ts,1,10) FROM dictations")}
        streak, day = 0, datetime.now().date()
        if day.isoformat() not in days:
            day -= timedelta(days=1)  # today not used yet: a streak through yesterday still counts
        while day.isoformat() in days:
            streak += 1
            day -= timedelta(days=1)
        wpm = total_words / (total_secs / 60) if total_secs > 0 else 0.0
        saved = max(0.0, total_words / TYPING_WPM - total_secs / 60)
        return Stats(words_today, total_words, count, wpm, saved, streak)
