# updater.py
import json
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import QMessageBox, QCheckBox, QWidget

DEBUG_UPDATER = True

# Central releases page
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

        if latest_entry is None or _compare_versions(
            version_str, latest_entry["version"]
        ) > 0:
            _dbg(f"  -> This is now the latest entry (previous: {latest_entry})")
            latest_entry = entry

        if _compare_versions(version_str, current_version) == 0:
            _dbg("  -> This matches current app version")
            current_entry = entry

    _dbg(f"Result of parse: latest_entry={latest_entry}, current_entry={current_entry}")
    return latest_entry, current_entry


class UpdateClient(QObject):
    """
    Handles background update checking and user dialogs.

    Usage from the main window:

        self._update_client = UpdateClient(
            parent_widget=self,
            app_version=APP_VERSION,
            descriptor_url=UPDATE_DESCRIPTOR_URL,
            os_tag=self._update_os_tag,
            get_skip_version=self._get_skip_version,
            set_skip_version=self._set_skip_version,
        )
        self._update_client.start()  # normal startup check

    A manual check that ignores snoozing can call:

        self._update_client.check_now(ignore_skip=True, result_callback=...)
    """

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

        # Per-request flag: if True, skip_version will be ignored.
        self._ignore_skip_for_this_request = False

        # Optional callback for the current request, used by manual checks
        # to communicate result state back to the UI.
        self._result_callback_for_this_request: Optional[Callable[[str], None]] = None

        _dbg(
            f"UpdateClient init: app_version={self._app_version}, "
            f"descriptor_url='{self._descriptor_url}', os_tag='{self._os_tag}'"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Perform the normal background update check (honours snoozing).
        """
        self._request_update(ignore_skip=False, result_callback=None)

    def check_now(
        self,
        ignore_skip: bool = False,
        result_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Explicit check triggered by the UI.

        If ignore_skip=True, this will ignore any snoozed skip_version and
        always show an available newer version.

        If result_callback is provided, it will be called with a string
        status code when the request finishes: "no_update",
        "update_available", "deprecated", or "error".
        """
        self._request_update(ignore_skip=ignore_skip, result_callback=result_callback)

    # ------------------------------------------------------------------
    # Network / descriptor handling
    # ------------------------------------------------------------------

    def _request_update(
        self,
        ignore_skip: bool,
        result_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if not self._os_tag:
            _dbg("_request_update: OS tag is empty, skipping update check")
            # Treat this as an error for manual checks
            if result_callback is not None:
                try:
                    result_callback("error")
                except Exception as e:
                    _dbg(
                        "_request_update: callback raised while reporting "
                        f"missing os_tag: {e!r}"
                    )
            return

        self._ignore_skip_for_this_request = ignore_skip
        self._result_callback_for_this_request = result_callback

        mode = "manual/ignore-skip" if ignore_skip else "normal"
        _dbg(
            f"_request_update: mode={mode}, starting GET to "
            f"'{self._descriptor_url}'"
        )

        request = QNetworkRequest(QUrl(self._descriptor_url))
        self._manager.get(request)

    def _on_update_reply(self, reply: QNetworkReply) -> None:
        try:
            err = reply.error()
            if err != QNetworkReply.NetworkError.NoError:
                _dbg(
                    f"_on_update_reply: network error {err} - "
                    f"{reply.errorString()}"
                )
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
            reply.deleteLater()

    def _handle_update_descriptor(self, text: str) -> None:
        if not self._os_tag:
            _dbg("_handle_update_descriptor: OS tag empty, aborting")
            self._notify_request_result("error")
            return

        _dbg("_handle_update_descriptor: starting parse and decision logic")

        latest_entry, current_entry = _parse_update_descriptor(
            text, self._os_tag, self._app_version
        )

        if not latest_entry:
            _dbg(
                "_handle_update_descriptor: no latest_entry for this OS, "
                "aborting"
            )
            self._notify_request_result("error")
            return

        _dbg(f"_handle_update_descriptor: latest_entry={latest_entry}")
        _dbg(f"_handle_update_descriptor: current_entry={current_entry}")

        current_is_deprecated = (
            current_entry is not None
            and isinstance(current_entry.get("flags"), list)
            and "deprecated" in current_entry["flags"]
        )

        _dbg(
            "_handle_update_descriptor: "
            f"current_is_deprecated={current_is_deprecated}"
        )

        if current_is_deprecated:
            _dbg(
                "_handle_update_descriptor: current version is deprecated, "
                "showing mandatory update dialog"
            )
            self._show_mandatory_update_dialog(latest_entry, current_entry)
            self._notify_request_result("deprecated")
            return

        cmp_latest_current = _compare_versions(
            latest_entry["version"], self._app_version
        )
        _dbg(
            "_handle_update_descriptor: compare latest("
            f"{latest_entry['version']}) vs current({self._app_version}) "
            f"-> {cmp_latest_current}"
        )

        if cmp_latest_current <= 0:
            _dbg(
                "_handle_update_descriptor: latest <= current, "
                "no update needed"
            )
            self._notify_request_result("no_update")
            return

        # Snooze behaviour (skip_version) only if this request is not ignoring it.
        if not self._ignore_skip_for_this_request:
            skip_version = self._get_skip_version()
            if skip_version:
                cmp_app_skip = _compare_versions(self._app_version, skip_version)
                cmp_latest_skip = _compare_versions(
                    latest_entry["version"], skip_version
                )
                _dbg(
                    "_handle_update_descriptor: skip_version is set -> "
                    f"skip_version={skip_version}, "
                    f"cmp_app_skip={cmp_app_skip}, "
                    f"cmp_latest_skip={cmp_latest_skip}"
                )
                if cmp_app_skip >= 0 and cmp_latest_skip <= 0:
                    _dbg(
                        "_handle_update_descriptor: snooze rule suppresses "
                        "this update"
                    )
                    self._notify_request_result("no_update")
                    return

        _dbg(
            "_handle_update_descriptor: conditions satisfied, "
            "showing optional update dialog"
        )
        self._show_optional_update_dialog(latest_entry)
        self._notify_request_result("update_available")

    def _notify_request_result(self, result: str) -> None:
        """
        Notify any per-request callback about the outcome of this check.

        The result string is one of: "no_update", "update_available",
        "deprecated", or "error".
        """
        cb = self._result_callback_for_this_request
        self._result_callback_for_this_request = None
        if cb is None:
            return
        try:
            cb(result)
        except Exception as e:
            _dbg(f"_notify_request_result: callback raised: {e!r}")

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _show_optional_update_dialog(self, latest_entry: dict) -> None:
        latest_version = latest_entry.get("version", "").strip()
        download_url = latest_entry.get("url", "").strip()

        _dbg(
            f"_show_optional_update_dialog: latest_version={latest_version}, "
            f"download_url='{download_url}', "
            f"current_version={self._app_version}"
        )

        if not latest_version:
            _dbg("_show_optional_update_dialog: latest_version is empty, aborting")
            return

        box = QMessageBox(self._parent_widget)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Update available")
        box.setText(
            f"There is a new version available: {latest_version}.\n"
            f"You are using version {self._app_version}."
        )

        checkbox = QCheckBox("Do not warn me until next version", box)
        box.setCheckBox(checkbox)

        download_button = box.addButton(
            "Download Update", QMessageBox.AcceptRole
        )
        releases_button = box.addButton(
            "Go to Releases Page", QMessageBox.ActionRole
        )
        skip_button = box.addButton(
            "Do Not Update", QMessageBox.RejectRole
        )
        box.setDefaultButton(download_button)

        box.exec()

        clicked = box.clickedButton()
        skip = checkbox.isChecked()

        if clicked is download_button and download_url:
            _dbg(f"_show_optional_update_dialog: opening download URL: {download_url}")
            QDesktopServices.openUrl(QUrl(download_url))
        elif clicked is releases_button:
            _dbg(
                "_show_optional_update_dialog: opening releases page: "
                f"{RELEASES_LATEST_URL}"
            )
            QDesktopServices.openUrl(QUrl(RELEASES_LATEST_URL))
        elif clicked is skip_button:
            _dbg("_show_optional_update_dialog: user chose 'Do Not Update'")

        if skip and latest_version:
            _dbg(
                "_show_optional_update_dialog: checkbox set, "
                f"setting skip_version to {latest_version}"
            )
            try:
                self._set_skip_version(latest_version)
            except Exception as e:
                _dbg(
                    "_show_optional_update_dialog: error while setting "
                    f"skip_version: {e!r}"
                )

    def _show_mandatory_update_dialog(
        self,
        latest_entry: dict,
        current_entry: Optional[dict],
    ) -> None:
        latest_version = latest_entry.get("version", "").strip() or self._app_version
        download_url = latest_entry.get("url", "").strip()

        if not download_url and current_entry is not None:
            download_url = current_entry.get("url", "").strip()

        _dbg(
            "_show_mandatory_update_dialog: "
            f"latest_version={latest_version}, download_url='{download_url}'"
        )

        box = QMessageBox(self._parent_widget)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Update required")
        box.setText(
            f"This version ({self._app_version}) has been marked as "
            f"deprecated.\nYou must update to version {latest_version} "
            "to continue using SoundBoard27."
        )

        download_button = box.addButton(
            "Download Update", QMessageBox.AcceptRole
        )
        releases_button = box.addButton(
            "Go to Releases Page", QMessageBox.ActionRole
        )
        quit_button = box.addButton("Quit", QMessageBox.RejectRole)
        box.setDefaultButton(download_button)

        box.exec()

        clicked = box.clickedButton()
        if clicked is download_button and download_url:
            _dbg(
                "_show_mandatory_update_dialog: user chose Download, "
                f"opening URL: {download_url}"
            )
            QDesktopServices.openUrl(QUrl(download_url))
        elif clicked is releases_button:
            _dbg(
                "_show_mandatory_update_dialog: user chose Releases Page, "
                f"opening {RELEASES_LATEST_URL}"
            )
            QDesktopServices.openUrl(QUrl(RELEASES_LATEST_URL))
        elif clicked is quit_button:
            _dbg("_show_mandatory_update_dialog: user chose Quit")

        _dbg("_show_mandatory_update_dialog: closing application due to mandatory update")
        # The owning widget (main window) is expected to close the app via this.
        self._parent_widget.close()
