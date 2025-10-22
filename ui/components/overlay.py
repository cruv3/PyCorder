from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, QRectF, QTimer


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._data = None
        self._screen_name = None
        self.show_Time = 2000

        self.enabled = True

    # =====================================================
    # Enable / Disable
    # =====================================================
    def enable(self, value: bool = True):
        """Globally enable or disable overlay drawing."""
        self.enabled = value
        if not value:
            self.hide()

    # =====================================================
    # Helpers
    # =====================================================
    def _move_to_screen(self, screen_name: str):
        screens = QApplication.screens()
        for s in screens:
            if screen_name in s.name() or s.name() in screen_name:
                geo = s.geometry()
                self.setGeometry(geo)
                return geo

        primary = QApplication.primaryScreen().geometry()
        self.setGeometry(primary)
        return primary

    # =====================================================
    # Drawing
    # =====================================================
    def show_move(self, path, screen_name="Unknown"):
        if not self.enabled:
            return
        self._data = ("move", path)
        self._screen_name = screen_name
        found_geo = self._move_to_screen(screen_name)

        if not found_geo:
            print(f"[WARN] Screen '{screen_name}' not found — using primary.")
        else:
            y_offset = found_geo.y()
            adjusted_path = [(x, y - y_offset) for x, y in path]
            self._data = ("move", adjusted_path)
        self.show()
        self.repaint()
        QTimer.singleShot(self.show_Time, self.hide)

    def show_click(self, x, y, screen_name="Unknown"):
        if not self.enabled:
            return
        self._data = ("click", x, y)
        self._screen_name = screen_name
        found_geo = self._move_to_screen(screen_name)

        if not found_geo:
            print(f"[WARN] Screen '{screen_name}' not found — using primary.")
        else:
            y_offset = found_geo.y()
            self._data = ("click", x, y - y_offset)
        self.show()
        self.repaint()
        QTimer.singleShot(self.show_Time, self.hide)
    
    def show_drag(self, path, screen_name="Unknown"):
        if not self.enabled:
            return
        self._data = ("drag", path)
        self._screen_name = screen_name
        found_geo = self._move_to_screen(screen_name)
        if not found_geo:
            print(f"[WARN] Screen '{screen_name}' not found — using primary.")
        else:
            y_offset = found_geo.y()
            adjusted_path = [(x, y - y_offset) for x, y in path]
            self._data = ("drag", adjusted_path)
        self.show()
        self.repaint()
        QTimer.singleShot(self.show_Time, self.hide)

    def hide(self):
        super().hide()
        self._data = None
        self._screen_name = None

    def paintEvent(self, event):
        if not self._data:
            return

        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        try:
            typ = self._data[0]
            
            if typ == "move":
                _, path = self._data
                if len(path) > 1:
                    pen = QPen(QColor(255, 0, 0, 180), 3)
                    qp.setPen(pen)
                    for i in range(1, len(path)):
                        x1, y1 = path[i - 1]
                        x2, y2 = path[i]
                        qp.drawLine(int(x1), int(y1), int(x2), int(y2))
                    x2, y2 = path[-1]
                    qp.setBrush(QBrush(QColor(255, 0, 0, 120)))
                    qp.drawEllipse(QRectF(x2 - 5, y2 - 5, 10, 10))

            elif typ == "click":
                _, x, y = self._data
                qp.setBrush(QBrush(QColor(0, 255, 0, 120)))
                qp.drawEllipse(QRectF(x - 10, y - 10, 20, 20))

            elif typ == "drag":
                _, path = self._data
                if len(path) > 1:
                    pen = QPen(QColor(255, 200, 0, 220), 3, Qt.DashLine)
                    qp.setPen(pen)
                    for i in range(1, len(path)):
                        x1, y1 = path[i - 1]
                        x2, y2 = path[i]
                        qp.drawLine(int(x1), int(y1), int(x2), int(y2))

                    x1, y1 = path[0]
                    qp.setBrush(QBrush(QColor(255, 0, 0, 180)))
                    qp.setPen(Qt.NoPen)
                    qp.drawEllipse(QRectF(x1 - 7, y1 - 7, 14, 14))

                    x2, y2 = path[-1]
                    qp.setBrush(QBrush(QColor(0, 255, 0, 180)))
                    qp.drawEllipse(QRectF(x2 - 7, y2 - 7, 14, 14))

        finally:
            qp.end()
