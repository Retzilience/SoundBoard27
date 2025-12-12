# theme.py (minimal change: make the stop-button outline thinner)

from PySide6.QtGui import QPalette, QColor


def apply_dark_theme(app):
    palette = QPalette()

    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(220, 220, 220))

    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.Text, QColor(220, 220, 220))

    palette.setColor(QPalette.Button, QColor(50, 50, 50))
    palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))

    palette.setColor(QPalette.Highlight, QColor(80, 80, 80))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    palette.setColor(QPalette.PlaceholderText, QColor(160, 160, 160))

    app.setPalette(palette)

    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }

        QLabel {
            color: #e0e0e0;
        }

        QPushButton {
            background-color: #333333;
            color: #e0e0e0;
            border: 1px solid #555555;
            padding: 6px;
        }

        QPushButton:hover {
            background-color: #444444;
        }

        QPushButton:pressed {
            background-color: #555555;
        }

        /* Stop buttons (main UI): thinner red pastel outline */
        QPushButton[stopButton="true"] {
            border: 1px solid #e57373;
        }

        QLineEdit {
            background-color: #202020;
            color: #e0e0e0;
            border: 1px solid #555555;
            selection-background-color: #555555;
            selection-color: #ffffff;
        }

        QScrollArea {
            background-color: #1e1e1e;
        }

        QFrame {
            background-color: #1e1e1e;
        }

        QAbstractScrollArea {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }

        QScrollBar:vertical {
            background-color: #2e2e2e;
            width: 12px;
            margin: 0px;
        }

        QScrollBar::handle:vertical {
            background-color: #555555;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
    """)
