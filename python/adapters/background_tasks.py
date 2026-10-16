"""Serial background I/O with queued Qt delivery and stale-request suppression."""
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal


class BackgroundTasks(QObject):
    completed = Signal(str, int, object, str)

    def __init__(self, parent=None, *, cancel_on_close=True):
        super().__init__(parent)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cst-file-reader")
        self.tokens = {}
        self.pending = {}
        self.closed = False
        self.cancel_on_close = cancel_on_close
        if parent is not None:
            parent.destroyed.connect(self.close)

    def submit(self, key, function, *args):
        """Replace a stale read request; use distinct keys for persistent writes."""
        if self.closed:
            raise RuntimeError("I/O worker is closed")
        token = self.tokens.get(key, 0) + 1
        self.tokens[key] = token
        previous = self.pending.get(key)
        if previous is not None:
            previous.cancel()
        future = self.executor.submit(function, *args)
        self.pending[key] = future

        def finished(result):
            if result.cancelled() or self.closed:
                return
            try:
                value, error = result.result(), ""
            except Exception as exc:
                value, error = None, str(exc)
            if not self.closed:
                self.completed.emit(key, token, value, error)
        future.add_done_callback(finished)
        return token

    def current(self, key, token):
        return not self.closed and self.tokens.get(key) == token

    def invalidate(self, key):
        self.tokens[key] = self.tokens.get(key, 0) + 1
        pending = self.pending.get(key)
        if pending is not None:
            pending.cancel()

    def close(self, *_args):
        if self.closed:
            return
        self.closed = True
        self.executor.shutdown(wait=True, cancel_futures=self.cancel_on_close)
        errors = []
        if not self.cancel_on_close:
            for future in self.pending.values():
                if not future.cancelled() and future.exception() is not None:
                    errors.append(str(future.exception()))
        self.pending.clear()
        if errors:
            raise RuntimeError("Persistent I/O did not complete: " + "; ".join(errors))
