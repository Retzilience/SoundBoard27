# utils.py
import os
import sys
import subprocess

from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl


def open_url_external(url) -> None:
    """
    Open a URL in the user's default browser / handler, with special care
    for Linux PyInstaller bundles where LD_LIBRARY_PATH can break KDE tools.

    On Linux:
      - Prefer calling xdg-open with a cleaned environment (no
        LD_LIBRARY_PATH / QT_* contaminating system helpers).
      - Fall back to QDesktopServices if that fails.

    On other platforms:
      - Use QDesktopServices directly.
    """
    if not url:
        return

    if isinstance(url, QUrl):
        qurl = url
        url_str = qurl.toString()
    else:
        url_str = str(url)
        qurl = QUrl(url_str)

    if sys.platform.startswith("linux"):
        try:
            env = os.environ.copy()
            # Remove variables that cause system helpers to load our
            # bundled Qt instead of the system Qt.
            for key in (
                "LD_LIBRARY_PATH",
                "QT_PLUGIN_PATH",
                "QT_QPA_PLATFORM_PLUGIN_PATH",
            ):
                env.pop(key, None)

            # Let PATH resolution find xdg-open; no hardcoded path.
            subprocess.Popen(["xdg-open", url_str], env=env)
            return
        except Exception:
            # Fall back to Qt below if xdg-open is unavailable or fails.
            pass

    try:
        QDesktopServices.openUrl(qurl)
    except Exception:
        # Nothing else we can do here in a portable way.
        pass
