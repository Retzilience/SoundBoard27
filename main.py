import sys

from PySide6.QtWidgets import QApplication

from theme import apply_dark_theme
from soundboard import Soundboard


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    wnd = Soundboard()
    wnd.resize(600, 600)
    wnd.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
