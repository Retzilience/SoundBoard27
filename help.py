# help.py
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QPushButton,
)

from settings import APP_NAME, APP_VERSION, CONFIG_FILE
from utils import open_url_external


ISSUES_URL = "https://github.com/Retzilience/SoundBoard27/issues"
RELEASES_LATEST_URL = "https://github.com/Retzilience/SoundBoard27/releases/latest"
REPO_URL = "https://github.com/Retzilience/SoundBoard27"


class HelpWindow(QWidget):
    """
    Read-only help / credits window.

    Text is selectable (for copy/paste) but not editable.
    Links are opened via a custom handler to avoid Qt / KDE / LD_LIBRARY_PATH
    issues inside PyInstaller bundles on Linux.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"{APP_NAME} — Help / About")
        self.setMinimumSize(860, 560)
        self.resize(860, 560)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        title = QLabel(f"{APP_NAME} {APP_VERSION}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        subtitle = QLabel("Help, About, Credits, and Support")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 11px; color: #b0b0b0;")

        text = QTextBrowser()
        text.setOpenExternalLinks(False)
        text.setOpenLinks(False)
        text.setReadOnly(True)
        text.anchorClicked.connect(self._on_anchor_clicked)

        platform_str = sys.platform
        config_path_str = str(CONFIG_FILE)

        html = f"""
<html>
  <head>
    <style>
      body {{
        font-family: sans-serif;
        line-height: 1.35;
        margin: 0;
        padding: 0;
      }}
      .wrap {{
        padding: 8px 10px;
      }}
      h1 {{
        font-size: 16px;
        margin: 0 0 10px 0;
      }}
      h2 {{
        font-size: 13px;
        margin: 16px 0 6px 0;
      }}
      p {{
        margin: 6px 0;
      }}
      ul {{
        margin: 6px 0 6px 18px;
        padding: 0;
      }}
      li {{
        margin: 4px 0;
      }}
      code {{
        font-family: monospace;
        background: #202020;
        padding: 1px 4px;
        border: 1px solid #444444;
        border-radius: 3px;
      }}
      .kv {{
        font-family: monospace;
        white-space: pre-wrap;
        background: #202020;
        border: 1px solid #444444;
        border-radius: 4px;
        padding: 8px;
        margin: 8px 0;
      }}
      .muted {{
        color: #b0b0b0;
      }}
      a {{
        text-decoration: none;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>{APP_NAME} — Help / About</h1>

      <h2>What this is</h2>
      <p>
        {APP_NAME} is a lightweight 3×9 soundboard (27 buttons) with two playback modes per button:
        one-shot and loop. Each button has an independent volume multiplier, and there is also a global volume control.
      </p>

      <h2>Quick use</h2>
      <ul>
        <li>Open <code>Load Sounds [Settings...]</code> to assign files and labels.</li>
        <li>Pick a mode per button: <code>one-shot</code> plays once, <code>loop</code> toggles looping on/off.</li>
        <li>Adjust per-button volume in the loader; adjust global volume in the main window.</li>
        <li>Use the stop controls in the main window to halt playback:
          <code>stop one-shot</code>, <code>stop loops</code>, or <code>stop all</code>.
        </li>
      </ul>

      <h2>Supported media</h2>
      <p class="muted">
        The loader accepts common audio/video formats (e.g. WAV/MP3/OGG/FLAC/MP4/MKV). Playback support depends on
        the QtMultimedia backend and available codecs on the system.
      </p>

      <h2>Configuration</h2>
      <p>
        Configuration is stored per user and includes button assignments, labels, per-button volume, global volume,
        and update snoozing state (if you choose to suppress update prompts for a specific release).
      </p>
      <div class="kv">Config file:
  {config_path_str}</div>

      <h2>Updates</h2>
      <p>
        On startup, the application may check for updates. Manual checking is available in the loader.
        The update check is an HTTP GET to the update descriptor file and (if you choose) opens GitHub release pages
        in your browser.
      </p>
      <ul>
        <li>Releases: <a href="{RELEASES_LATEST_URL}">{RELEASES_LATEST_URL}</a></li>
        <li>Repository: <a href="{REPO_URL}">{REPO_URL}</a></li>
      </ul>

      <h2>Support / bug reports</h2>
      <p>
        If you hit a crash or playback issue, include your OS, {APP_NAME} version, the file type you loaded, and any console output.
      </p>
      <ul>
        <li>Report an issue: <a href="{ISSUES_URL}">{ISSUES_URL}</a></li>
      </ul>

      <h2>Credits</h2>
      <ul>
        <li>Author: Retzilience</li>
        <li>UI: Qt / PySide6</li>
        <li>Media decoding: QtMultimedia (often backed by FFmpeg / system codecs depending on platform)</li>
        <li>Hosting / releases: GitHub</li>
      </ul>

      <h2>Build info</h2>
      <div class="kv">Version:
  {APP_VERSION}

Platform:
  {platform_str}</div>

      <p class="muted">
        License: see the <code>LICENSE</code> file in the repository.
      </p>
    </div>
  </body>
</html>
"""
        text.setHtml(html)

        button_bar = QHBoxLayout()
        button_bar.setContentsMargins(0, 0, 0, 0)
        button_bar.setSpacing(8)

        report_button = QPushButton("Report Bug")
        report_button.setFixedHeight(34)
        report_button.clicked.connect(self._on_report_bug_clicked)

        close_button = QPushButton("Close")
        close_button.setFixedHeight(34)
        close_button.clicked.connect(self.close)

        button_bar.addWidget(report_button)
        button_bar.addStretch(1)
        button_bar.addWidget(close_button)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(text, 1)
        main_layout.addLayout(button_bar)

    def _on_anchor_clicked(self, url):
        try:
            open_url_external(url)
        except Exception:
            pass

    def _on_report_bug_clicked(self):
        try:
            open_url_external(ISSUES_URL)
        except Exception:
            pass
