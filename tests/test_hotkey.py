import types

import keyboard
import pytest

from murmur.engine import hotkey as hk_mod
from murmur.engine.hotkey import Hotkey

D, U = keyboard.KEY_DOWN, keyboard.KEY_UP


@pytest.fixture
def clock(monkeypatch):
    t = [100.0]
    monkeypatch.setattr(hk_mod.time, "monotonic", lambda: t[0])
    return t


def make(keys=("ctrl", "alt"), hands_free=True):
    log = []
    hk = Hotkey(list(keys), on_start=lambda hf: log.append("hands_free" if hf else "start"),
                on_stop=lambda: log.append("stop"), on_cancel=lambda: log.append("cancel"),
                min_hold=0.3, hands_free=hands_free)
    ev = lambda name, kind: hk._on_event(types.SimpleNamespace(name=name, event_type=kind))  # noqa: E731
    return hk, ev, log


def test_hold_to_talk(clock):
    _, ev, log = make()
    ev("left ctrl", D); ev("alt", D); ev("alt", D)  # repeat is ignored
    clock[0] += 1.0
    ev("alt", U); ev("left ctrl", U)
    assert log == ["start", "stop"]


def test_other_key_cancels_so_shortcuts_still_work(clock):
    _, ev, log = make()
    ev("ctrl", D); ev("alt", D); ev("t", D); ev("t", U); ev("alt", U); ev("ctrl", U)
    assert log == ["start", "cancel"]


def test_combo_after_other_key_is_blocked(clock):
    _, ev, log = make()
    ev("ctrl", D); ev("c", D); ev("c", U); ev("alt", D); ev("alt", U); ev("ctrl", U)
    assert log == []


def test_short_tap_is_cancelled(clock):
    _, ev, log = make(hands_free=False)
    ev("ctrl", D); ev("alt", D); clock[0] += 0.1; ev("alt", U); ev("ctrl", U)
    assert log == ["start", "cancel"]


def test_double_tap_enters_hands_free_and_tap_stops(clock):
    _, ev, log = make()
    for _ in range(2):
        ev("ctrl", D); ev("alt", D); clock[0] += 0.1; ev("alt", U); ev("ctrl", U); clock[0] += 0.1
    assert log[-1] == "hands_free"
    ev("x", D); ev("x", U)  # typing while hands-free does not stop it
    assert log[-1] == "hands_free"
    clock[0] += 5
    ev("ctrl", D); ev("alt", D)
    assert log[-1] == "stop"
    ev("alt", U); ev("ctrl", U)
    assert log.count("stop") == 1


def test_escape_cancels_hands_free(clock):
    _, ev, log = make()
    for _ in range(2):
        ev("ctrl", D); ev("alt", D); clock[0] += 0.1; ev("alt", U); ev("ctrl", U); clock[0] += 0.1
    ev("esc", D)
    assert log[-1] == "cancel"


def test_exact_key_spec(clock):
    _, ev, log = make(keys=("right ctrl",))
    ev("left ctrl", D); ev("left ctrl", U)
    assert log == []
    ev("right ctrl", D); clock[0] += 1; ev("right ctrl", U)
    assert log == ["start", "stop"]


def test_paused_ignores_everything(clock):
    hk, ev, log = make()
    hk.paused = True
    ev("ctrl", D); ev("alt", D); clock[0] += 1; ev("alt", U); ev("ctrl", U)
    assert log == []
