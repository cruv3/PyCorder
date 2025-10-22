from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QPoint
import queue


class ScreenFetcher(QObject):
    """Thread-safe interface to query the screen name at a given (x, y) position."""

    request_signal = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self._result_queue = queue.Queue()
        self.request_signal.connect(self._handle_request)

    # =====================================================
    # Public API
    # =====================================================
    def get_name(self, x: float, y: float) -> str:
        """Return the screen name for the given (x, y) coordinates."""
        self.request_signal.emit(x, y)
        try:
            return self._result_queue.get(timeout=0.2)
        except queue.Empty:
            return "Unknown"

    # =====================================================
    # Internal slot
    # =====================================================
    def _handle_request(self, x: float, y: float):
        """Executed in the Qt (GUI) thread."""
        screen = QApplication.screenAt(QPoint(int(x), int(y)))
        name = screen.name() if screen else "Unknown"
        self._result_queue.put(name)
