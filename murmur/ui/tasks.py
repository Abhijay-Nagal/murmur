"""Run blocking work off the UI thread and deliver the result back on it."""
import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal

log = logging.getLogger(__name__)


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(float, str)


class _Task(QRunnable):
    def __init__(self, fn, with_progress):
        super().__init__()
        self.fn, self.with_progress = fn, with_progress
        self.signals = _Signals()

    def run(self):
        try:
            if self.with_progress:
                result = self.fn(lambda frac, msg: self.signals.progress.emit(frac, msg))
            else:
                result = self.fn()
        except Exception as e:
            log.exception("Background task failed")
            outcome = (self.signals.failed, str(e))
        else:
            outcome = (self.signals.done, result)
        try:
            outcome[0].emit(outcome[1])
        except RuntimeError:
            pass  # the app quit while this task was running


_keep: set = set()  # hold references until the task finishes


def run_async(fn: Callable, on_done: Callable[[Any], None] | None = None,
              on_error: Callable[[str], None] | None = None,
              on_progress: Callable[[float, str], None] | None = None):
    task = _Task(fn, on_progress is not None)
    sig = task.signals
    _keep.add(sig)
    # Queued: callbacks run on the UI thread, where `sig` was created.
    q = Qt.QueuedConnection
    if on_done:
        sig.done.connect(on_done, q)
    if on_error:
        sig.failed.connect(on_error, q)
    if on_progress:
        sig.progress.connect(on_progress, q)
    sig.done.connect(lambda _: _keep.discard(sig))
    sig.failed.connect(lambda _: _keep.discard(sig))
    QThreadPool.globalInstance().start(task)
