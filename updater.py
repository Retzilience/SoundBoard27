# updater.py (minimal change: prevent overlapping checks + ensure dialogs appear on top + add a timeout)

from typing import Callable, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, QUrl, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import QMessageBox, QCheckBox, QWidget, QApplication

from utils import open_url_external

DEBUG_UPDATER = True
RELEASES_LATEST_URL = "https://github.com/Retzilience/SoundBoard27/releases/latest"


def _dbg(msg: str) -> None:
    if DEBUG_UPDATER:
        print(f"[SoundBoard27][update] {msg}", flush=True)


def _parse_version(version_str: str) -> Tuple[int, ...]:
    parts = []
    for part in str(version_str).strip().split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _compare_versions(a: str, b: str) -> int:
    ta = _parse_version(a)
    tb = _parse_version(b)
    length = max(len(ta), len(tb))
    ta = ta + (0,) * (length - len(ta))
    tb = tb + (0,) * (length - len(tb))
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def _parse_update_descriptor(
    text: str,
    os_tag: str,
    current_version: str,
) -> Tuple[Optional[dict], Optional[dict]]:
    _dbg(
        f"Parsing update descriptor for os_tag='{os_tag}', "
        f"current_version='{current_version}'"
    )
    latest_entry: Optional[dict] = None
    current_entry: Optional[dict] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 4:
            _dbg(f"Skipping malformed line: {raw_line!r}")
            continue

        version_str, os_name, flags_str, url = parts
        if os_name.lower() != os_tag.lower():
            continue

        flags = [f.strip().lower() for f in flags_str.split(",") if f.strip()]
        entry = {
            "version": version_str,
            "flags": flags,
            "url": url,
        }

        _dbg(
            "Found entry for this OS: "
            f"version='{version_str}', flags={flags}, url='{url}'"
        )

        if latest_entry is None or _compare_versions(version_str, latest_entry["version"]) > 0:
            _dbg(f"  -> This is now the latest entry (previous: {latest_entry})")
            latest_entry = entry

        if _compare_versions(version_str, current_version) == 0:
            _dbg("  -> This matches current app version")
            current_entry = entry

    _dbg(f"Result of parse: latest_entry={latest_entry}, current_entry={current_entry}")
    return latest_entry, current_entry


class UpdateClient(QObject):
    def __init__(
        self,
        parent_widget: QWidget,
        app_version: str,
        descriptor_url: str,
        os_tag: str,
        get_skip_version: Callable[[], Optional[str]],
        set_skip_version: Callable[[Optional[str]], None],
    ):
        super().__init__(parent_widget)

        self._parent_widget = parent_widget
        self._app_version = str(app_version)
        self._descriptor_url = descriptor_url
        self._os_tag = os_tag
        self._get_skip_version = get_skip_version
        self._set_skip_version = set_skip_version

        self._manager = QNetworkAccessManager(self)
        self._manager.finished.connect(self._on_update_reply)

        self._ignore_skip_for_this_request = False
        self._result_callback_for_this_request: Optional[Callable[[str], None]] = None

        # Minimal guard against overlapping checks / stacked modal dialogs.
        self._in_flight = False

        _dbg(
            f"UpdateClient init: app_version={self._app_version}, "
            f"descriptor_url='{self._descriptor_url}', os_tag='{self._os_tag}'"
        )

    def start(self) -> None:
        self._request_update(ignore_skip=False, result_callback=None)

    def check_now(
        self,
        ignore_skip: bool = False,
        result_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._request_update(ignore_skip=ignore_skip, result_callback=result_callback)

    def _request_update(
        self,
        ignore_skip: bool,
        result_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if not self._os_tag:
            _dbg("_request_update: OS tag is empty, skipping update check")
            if result_callback is not None:
                try:
                    result_callback("error")
                except Exception as e:
                    _dbg(f"_request_update: callback raised while reporting missing os_tag: {e!r}")
            return

        if self._in_flight:
            _dbg("_request_update: request already in flight; ignoring")
            if result_callback is not None:
                try:
                    result_callback("error")
                except Exception as e:
                    _dbg(f"_request_update: callback raised while reporting in-flight: {e!r}")
            return

        self._in_flight = True
        self._ignore_skip_for_this_request = ignore_skip
        self._result_callback_for_this_request = result_callback

        mode = "manual/ignore-skip" if ignore_skip else "normal"
        _dbg(f"_request_update: mode={mode}, starting GET to '{self._descriptor_url}'")

        request = QNetworkRequest(QUrl(self._descriptor_url))
        reply = self._manager.get(request)

        # Timeout to avoid a stuck in-flight state (and user-perceived “stall”).
        timer = QTimer(self)
        timer.setSingleShot(True)

        def on_timeout() -> None:
            try:
                if reply.isRunning():
                    _dbg("_request_update: network timeout; aborting reply")
                    reply.abort()
            except Exception as e:
                _dbg(f"_request_update: exception during abort: {e!r}")

        timer.timeout.connect(on_timeout)
        timer.start(8000)

        def cleanup_timer() -> None:
            timer.stop()
            timer.deleteLater()

        reply.finished.connect(cleanup_timer)

    def _on_update_reply(self, reply: QNetworkReply) -> None:
        try:
            err = reply.error()
            if err != QNetworkReply.NetworkError.NoError:
                _dbg(f"_on_update_reply: network error {err} - {reply.errorString()}")
                self._notify_request_result("error")
                return

            data = reply.readAll()
            try:
                text = bytes(data).decode("utf-8", errors="replace")
            except Exception as e:
                _dbg(f"_on_update_reply: decode failed: {e!r}")
                self._notify_request_result("error")
                return

            _dbg(f"_on_update_reply: received descriptor ({len(text)} bytes)")
            for i, line in enumerate(text.splitlines()[:5]):
                _dbg(f"  line[{i}]: {line!r}")

            self._handle_update_descriptor(text)
        finally:
            self._in_flight = False
            reply.deleteLater()

    def _handle_update_descriptor(self, text: str) -> None:
        if not self._os_tag:
            _dbg("_handle_update_descriptor: OS tag empty, aborting")
            self._notify_request_result("error")
            return

        _dbg("_handle_update_descriptor: starting parse and decision logic")

        latest_entry, current_entry = _parse_update_descriptor(text, self._os_tag, self._app_version)

        if not latest_entry:
            _dbg("_handle_update_descriptor: no latest_entry for this OS, aborting")
            self._notify_request_result("error")
            return

        current_is_deprecated = (
            current_entry is not None
            and isinstance(current_entry.get("flags"), list)
            and "deprecated" in current_entry["flags"]
        )

        if current_is_deprecated:
            self._show_mandatory_update_dialog(latest_entry, current_entry)
            self._notify_request_result("deprecated")
            return

        cmp_latest_current = _compare_versions(latest_entry["version"], self._app_version)
        if cmp_latest_current <= 0:
            self._notify_request_result("no_update")
            return

        if not self._ignore_skip_for_this_request:
            skip_version = self._get_skip_version()
            if skip_version:
                cmp_app_skip = _compare_versions(self._app_version, skip_version)
                cmp_latest_skip = _compare_versions(latest_entry["version"], skip_version)
                if cmp_app_skip >= 0 and cmp_latest_skip <= 0:
                    self._notify_request_result("no_update")
                    return

        self._show_optional_update_dialog(latest_entry)
        self._notify_request_result("update_available")

    def _notify_request_result(self, result: str) -> None:
        cb = self._result_callback_for_this_request
        self._result_callback_for_this_request = None
        if cb is None:
            return
        try:
            cb(result)
        except Exception as e:
            _dbg(f"_notify_request_result: callback raised: {e!r}")

    def _effective_dialog_parent(self) -> QWidget:
        w = QApplication.activeWindow()
        return w if w is not None else self._parent_widget

    def _prepare_box(self, box: QMessageBox) -> None:
        # Prevent “frozen app” perception caused by a modal box appearing behind another window.
        box.setWindowModality(Qt.ApplicationModal)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        try:
            box.raise_()
            box.activateWindow()
        except Exception:
            pass

    def _show_optional_update_dialog(self, latest_entry: dict) -> None:
        latest_version = latest_entry.get("version", "").strip()
        download_url = latest_entry.get("url", "").strip()

        if not latest_version:
            return

        box = QMessageBox(self._effective_dialog_parent())
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Update available")
        box.setText(
            f"There is a new version available: {latest_version}.\n"
            f"You are using version {self._app_version}."
        )

        checkbox = QCheckBox("Do not warn me until next version", box)
        box.setCheckBox(checkbox)

        download_button = box.addButton("Download Update", QMessageBox.NoRole)
        releases_button = box.addButton("Go to Releases Page", QMessageBox.NoRole)
        skip_button = box.addButton("Do Not Update", QMessageBox.NoRole)
        box.setDefaultButton(download_button)

        self._prepare_box(box)
        box.exec()

        clicked = box.clickedButton()
        skip = checkbox.isChecked()

        if clicked is download_button and download_url:
            open_url_external(download_url)
        elif clicked is releases_button:
            open_url_external(RELEASES_LATEST_URL)
        elif clicked is skip_button:
            pass

        if skip and latest_version:
            try:
                self._set_skip_version(latest_version)
            except Exception as e:
                _dbg(f"_show_optional_update_dialog: error while setting skip_version: {e!r}")

    def _show_mandatory_update_dialog(
        self,
        latest_entry: dict,
        current_entry: Optional[dict],
    ) -> None:
        latest_version = latest_entry.get("version", "").strip() or self._app_version
        download_url = latest_entry.get("url", "").strip()

        if not download_url and current_entry is not None:
            download_url = current_entry.get("url", "").strip()

        box = QMessageBox(self._effective_dialog_parent())
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Update required")
        box.setText(
            f"This version ({self._app_version}) has been marked as deprecated.\n"
            f"You must update to version {latest_version} to continue using SoundBoard27."
        )

        download_button = box.addButton("Download Update", QMessageBox.NoRole)
        releases_button = box.addButton("Go to Releases Page", QMessageBox.NoRole)
        quit_button = box.addButton("Quit", QMessageBox.NoRole)
        box.setDefaultButton(download_button)

        self._prepare_box(box)
        box.exec()

        clicked = box.clickedButton()
        if clicked is download_button and download_url:
            open_url_external(download_url)
        elif clicked is releases_button:
            open_url_external(RELEASES_LATEST_URL)
        elif clicked is quit_button:
            pass

        self._parent_widget.close()
