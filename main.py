import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QCursor
from ui.main_window import MainWindow


__version__ = "1.0.0"

def run():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowTitle(f"PyCorder v{__version__}")

    # Fenster auf aktuellem Monitor positionieren
    screen = app.screenAt(QCursor.pos())
    if screen:
        geo = screen.availableGeometry()
        win.move(geo.x() + 100, geo.y() + 100)

    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run()
