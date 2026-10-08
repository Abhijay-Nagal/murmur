from datetime import datetime, timedelta

from murmur.storage import Storage


def test_stats_and_search(tmp_path):
    s = Storage(tmp_path / "h.db")
    s.add("raw one", "hello world from murmur", "Chrome", 3.0)
    s.add("raw two", "second dictation here", "Slack", 3.0)
    st = s.stats()
    assert st.words_total == 7 and st.words_today == 7 and st.dictations_total == 2
    assert round(st.avg_wpm) == 70  # 7 words in 6 seconds
    assert st.streak_days == 1
    assert [d.app for d in s.recent(search="slack")] == ["Slack"]


def test_streak_counts_consecutive_days(tmp_path):
    s = Storage(tmp_path / "h.db")
    for days_ago in (0, 1, 2, 4):
        d = s.add("x", "a b", "", 1)
        ts = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
        s._db.execute("UPDATE dictations SET ts=? WHERE id=?", (ts, d.id))
    s._db.commit()
    assert s.stats().streak_days == 3


def test_delete_and_clear(tmp_path):
    s = Storage(tmp_path / "h.db")
    a = s.add("x", "one", "", 1)
    s.add("y", "two", "", 1)
    s.delete(a.id)
    assert [d.final for d in s.recent()] == ["two"]
    s.clear()
    assert s.recent() == []
