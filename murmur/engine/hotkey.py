"""Hotkey handling for a modifier-only combo like Ctrl+Alt.

- Hold the combo to record; release to finish.
- Double-tap the combo to record hands-free; tap it once more to finish (Esc cancels).
- Pressing any other key while holding cancels, so real shortcuts such as Ctrl+Alt+Del
  or Ctrl+Alt+T keep working and never trigger a dictation.

Keys are either groups ("ctrl", "alt", "shift", "windows", matching left or right) or exact
key names such as "right ctrl".
"""
import logging
import time
from typing import Callable

import keyboard

log = logging.getLogger(__name__)

GROUPS = ("ctrl", "alt", "shift", "windows")
DOUBLE_TAP_SECONDS = 0.45


def _matches(spec: str, name: str) -> bool:
    return spec in name if spec in GROUPS else spec == name


class Hotkey:
    def __init__(
        self,
        keys: list[str],
        on_start: Callable[[bool], None],  # arg: hands_free
        on_stop: Callable[[], None],
        on_cancel: Callable[[], None],
        min_hold: float = 0.3,
        hands_free: bool = True,
    ):
        self.keys = [k.lower() for k in keys]
        self.min_hold = min_hold
        self.hands_free = hands_free
        self.on_start, self.on_stop, self.on_cancel = on_start, on_stop, on_cancel
        self.paused = False
        self._down: set[str] = set()
        self._holding = False  # recording while the combo is held
        self._locked = False  # hands-free recording
        self._blocked = False  # another key was used with the modifiers; wait for full release
        self._started = 0.0
        self._last_tap = 0.0
        self._hook = None

    def start(self):
        self._hook = keyboard.hook(self._on_event)

    def stop(self):
        if self._hook:
            keyboard.unhook(self._hook)
            self._hook = None

    def reset(self):
        """Forget an in-progress recording, e.g. after the app stopped it on its own."""
        self._holding = self._locked = False

    def _spec_for(self, name: str) -> str | None:
        return next((k for k in self.keys if _matches(k, name)), None)

    def _on_event(self, event: keyboard.KeyboardEvent):
        # Runs on the keyboard hook thread: must stay fast, callbacks only flip state.
        if self.paused:
            return
        name = (event.name or "").lower()
        spec = self._spec_for(name)
        now = time.monotonic()

        if event.event_type == keyboard.KEY_DOWN:
            if spec is None:
                if self._locked and name == "esc":
                    self._locked = False
                    self.on_cancel()
                elif self._holding:
                    self._holding = False
                    self.on_cancel()
                if self._down:
                    self._blocked = True
                return
            if spec in self._down:
                return  # key repeat
            self._down.add(spec)
            if len(self._down) == len(self.keys) and not self._blocked:
                if self._locked:
                    self._locked = False
                    self.on_stop()
                elif not self._holding:
                    self._holding = True
                    self._started = now
                    self.on_start(False)
        else:
            if spec is None or spec not in self._down:
                return
            self._down.discard(spec)
            if self._holding:
                self._holding = False
                if now - self._started >= self.min_hold:
                    self.on_stop()
                else:
                    self.on_cancel()
                    if self.hands_free and now - self._last_tap < DOUBLE_TAP_SECONDS:
                        self._locked = True
                        self._last_tap = 0.0
                        self.on_start(True)
                    else:
                        self._last_tap = now
            if not self._down:
                self._blocked = False
