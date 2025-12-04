# help.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QPushButton,
)
from settings import APP_NAME, APP_VERSION


class HelpWindow(QWidget):
    """
    Simple read-only help / credits window.

    Text is selectable (for copy/paste) but not editable.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"{APP_NAME} — Help / Credits")
        # Make it roughly the same size as the Load Sounds window
        self.setMinimumSize(800, 500)
        self.resize(800, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        title = QLabel(f"{APP_NAME} {APP_VERSION}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        subtitle = QLabel("Help, Credits and Information")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 11px;")

        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setOpenLinks(True)
        text.setReadOnly(True)

        # HTML content with clickable links; formatting kept close to the
        # original plain-text version.
        html = f"""
<html>
  <body style="font-family: monospace; white-space: pre;">
SoundBoard27 — Help / Credits
================================

Application
-----------
Name:     {APP_NAME}
Version:  {APP_VERSION}

Description:
  A lightweight 3x9 soundboard with per-button loop/one-shot modes
  and independent volume controls, built with PySide6 / Qt.

Author
------
  Retzilience
  GitHub:  <a href="https://github.com/Retzilience">https://github.com/Retzilience</a>
  Project: <a href="https://github.com/Retzilience/SoundBoard27">https://github.com/Retzilience/SoundBoard27</a>

Updates
-------
  • The application can check for updates automatically on startup.
  • You can manually trigger a check from the "Load Sounds" window
    using the "Check for Updates" button.
  • Releases page:
      <a href="https://github.com/Retzilience/SoundBoard27/releases/latest">
      https://github.com/Retzilience/SoundBoard27/releases/latest
      </a>

Configuration
-------------
  • Per-user configuration file:
      - See resolve_config_path() in settings.py for exact location.
  • Stores:
      - Button assignments (path, label, mode, per-button volume)
      - Global volume
      - Update snooze version (if you choose "Do Not Update" for a release)

License
-------
  This program is open source software.
  See the LICENSE file in the repository for full terms:
      <a href="https://github.com/Retzilience/SoundBoard27">
      https://github.com/Retzilience/SoundBoard27
      </a>

Acknowledgements
----------------
  • Qt / PySide6 for the UI and multimedia stack.
  • FFmpeg via QtMultimedia for audio/video decoding.

Notes
-----
  • Some media formats depend on system codecs.
  • If audio fails to play, check your system audio routing
    and available codecs for the given file type.
  </body>
</html>
"""
        text.setHtml(html)

        button_bar = QHBoxLayout()
        button_bar.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_bar.addWidget(close_button)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(text, 1)
        main_layout.addLayout(button_bar)
