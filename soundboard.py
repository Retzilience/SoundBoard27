# soundboard.py
import os
import json
from typing import Optional, Callable

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QSlider
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from settings import CONFIG_FILE, APP_VERSION, UPDATE_DESCRIPTOR_URL, get_os_tag
from widgets import SoundButton, LoadWindow
from updater import UpdateClient
from help import HelpWindow


DEBUG_SOUNDBOARD = True

STOP_OUTLINE_COLOR = "#e57373"
STOP_FLASH_COLOR = "#e57373"
STOP_FLASH_MS = 500


def _dbg(msg: str) -> None:
    if DEBUG_SOUNDBOARD:
        print(f"[SoundBoard27][core] {msg}", flush=True)


class Soundboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SoundBoard27")

        _dbg(f"Soundboard init: APP_VERSION={APP_VERSION}, CONFIG_FILE='{CONFIG_FILE}'")

        # One-shot player
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)

        # Loop players per button
        self.loop_players = {}

        self.current_button: Optional[SoundButton] = None
        self.current_page = 0
        self.volume = 1.0  # global volume 0.0–1.0

        # Update state
        self.update_skip_version: Optional[str] = None
        self._update_os_tag = get_os_tag()
        self._update_client: Optional[UpdateClient] = None

        # Help window (lazy-created)
        self._help_window: Optional[HelpWindow] = None

        _dbg(f"Detected OS tag: '{self._update_os_tag}'")

        # Buttons
        self.buttons = [SoundButton(i) for i in range(27)]
        for btn in self.buttons:
            btn.clicked.connect(lambda _, b=btn: self.play_sound(b))

        # Load configuration (buttons, volume, update skip_version)
        self.load_config()
        _dbg(
            f"Config loaded: global_volume={self.volume}, "
            f"update_skip_version={self.update_skip_version}"
        )

        # Layouts
        main_layout = QVBoxLayout(self)
        top_bar = QHBoxLayout()
        bottom_bar = QHBoxLayout()
        controls_bar = QHBoxLayout()

        self.page_label = QLabel("[1]")
        self.page_label.setAlignment(Qt.AlignCenter)
        prev_button = QPushButton("<")
        next_button = QPushButton(">")

        prev_button.clicked.connect(self.prev_page)
        next_button.clicked.connect(self.next_page)

        top_bar.addWidget(prev_button)
        top_bar.addWidget(self.page_label)
        top_bar.addWidget(next_button)

        self.grid = QGridLayout()

        bottom_button = QPushButton("Load Sounds [Settings...]")
        bottom_button.clicked.connect(self.open_loader)
        bottom_bar.addWidget(bottom_button)

        # Stop controls (with red pastel outline + flash fill on click)
        stop_one_shot_button = QPushButton("stop one-shot")
        stop_loops_button = QPushButton("stop loops")
        stop_all_button = QPushButton("stop all")

        self._mark_stop_button(stop_one_shot_button)
        self._mark_stop_button(stop_loops_button)
        self._mark_stop_button(stop_all_button)

        stop_one_shot_button.clicked.connect(
            lambda _checked=False, b=stop_one_shot_button: self._flash_and_call(b, self.stop_one_shots)
        )
        stop_loops_button.clicked.connect(
            lambda _checked=False, b=stop_loops_button: self._flash_and_call(b, self.stop_loops)
        )
        stop_all_button.clicked.connect(
            lambda _checked=False, b=stop_all_button: self._flash_and_call(b, self.stop_all)
        )

        # Global volume slider
        volume_label = QLabel("Volume")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setSingleStep(5)
        self.volume_slider.setFixedWidth(160)
        self.volume_slider.setValue(int(self.volume * 100))
        self.volume_slider.valueChanged.connect(self.on_volume_changed)

        controls_bar.addWidget(stop_one_shot_button)
        controls_bar.addWidget(stop_loops_button)
        controls_bar.addWidget(stop_all_button)
        controls_bar.addStretch()
        controls_bar.addWidget(volume_label)
        controls_bar.addWidget(self.volume_slider)

        main_layout.addLayout(top_bar)
        main_layout.addLayout(self.grid)
        main_layout.addLayout(bottom_bar)
        main_layout.addLayout(controls_bar)

        self.update_page()

        self.player.mediaStatusChanged.connect(self.on_status_changed)

        # Apply initial volume to audio outputs
        self.refresh_volumes()

        # Start background update check (non-blocking)
        self._setup_update_checker()

    # --- Stop button visuals ---

    def _mark_stop_button(self, btn: QPushButton) -> None:
        btn.setProperty("stopButton", True)
        try:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        except Exception:
            pass

    def _flash_button(self, btn: QPushButton, duration_ms: int = STOP_FLASH_MS) -> None:
        if btn is None:
            return

        original_style = btn.styleSheet()

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STOP_FLASH_COLOR};
                color: #ffffff;
                border: 1px solid {STOP_OUTLINE_COLOR};
                padding: 6px;
            }}
        """)

        timer = QTimer(self)
        timer.setSingleShot(True)

        def restore() -> None:
            btn.setStyleSheet(original_style)
            timer.deleteLater()
            try:
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()
            except Exception:
                pass

        timer.timeout.connect(restore)
        timer.start(duration_ms)

    def _flash_and_call(self, btn: QPushButton, fn: Callable[[], None]) -> None:
        try:
            self._flash_button(btn, STOP_FLASH_MS)
        except Exception as e:
            _dbg(f"_flash_and_call: flash failed: {e!r}")

        try:
            fn()
        except Exception as e:
            _dbg(f"_flash_and_call: stop action failed: {e!r}")

    # --- Paging / layout ---

    def update_page(self):
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        start = self.current_page * 9
        for offset, btn_index in enumerate(range(start, start + 9)):
            r = offset // 3
            c = offset % 3
            self.grid.addWidget(self.buttons[btn_index], r, c)

        self.page_label.setText(f"[{self.current_page + 1}]")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page()

    def next_page(self):
        if self.current_page < 2:
            self.current_page += 1
            self.update_page()

    # --- Audio / playback ---

    def refresh_volumes(self):
        # One-shot player
        if self.current_button and not self.current_button.is_loop:
            self.audio.setVolume(self.volume * self.current_button.button_volume)
        else:
            self.audio.setVolume(self.volume)

        # Loop players
        for btn, (player, audio) in self.loop_players.items():
            audio.setVolume(self.volume * btn.button_volume)

    def play_sound(self, btn: SoundButton):
        if not btn.sound_path or not os.path.isfile(btn.sound_path):
            return

        if btn.is_loop:
            # Toggle loop on/off for this button
            if btn in self.loop_players:
                player, audio = self.loop_players.pop(btn)
                player.stop()
                btn.set_playing(False)
                player.deleteLater()
                audio.deleteLater()
            else:
                player = QMediaPlayer(self)
                audio = QAudioOutput(self)
                player.setAudioOutput(audio)
                player.setSource(QUrl.fromLocalFile(btn.sound_path))
                player.setLoops(QMediaPlayer.Infinite)
                self.loop_players[btn] = (player, audio)
                btn.set_playing(True)
                self.refresh_volumes()
                player.play()
            return

        # One-shot behaviour: stop previous one-shot, leave loops untouched
        if self.current_button and not self.current_button.is_loop:
            self.current_button.set_playing(False)

        self.player.stop()

        self.current_button = btn
        btn.set_playing(True)

        self.player.setSource(QUrl.fromLocalFile(btn.sound_path))
        self.refresh_volumes()
        self.player.play()

    def on_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.current_button and not self.current_button.is_loop:
                self.current_button.set_playing(False)
                self.current_button = None
                self.refresh_volumes()

    # --- UI actions ---

    def open_loader(self):
        loader = LoadWindow(
            self.buttons,
            self.save_config,
            check_updates_callback=self._manual_update_check,
            help_callback=self._show_help_window,
            parent=self,
        )
        loader.resize(900, 600)
        loader.show()

    def stop_one_shots(self):
        if self.current_button and not self.current_button.is_loop:
            self.current_button.set_playing(False)
        self.player.stop()
        self.current_button = None
        self.refresh_volumes()

    def stop_loops(self):
        for btn, (player, audio) in list(self.loop_players.items()):
            player.stop()
            btn.set_playing(False)
            player.deleteLater()
            audio.deleteLater()
        self.loop_players.clear()
        self.refresh_volumes()

    def stop_all(self):
        self.stop_one_shots()
        self.stop_loops()

    def on_volume_changed(self, value):
        self.volume = value / 100.0
        self.refresh_volumes()

    # --- Config persistence ---

    def save_config(self):
        button_items = []
        for btn in self.buttons:
            button_items.append(
                {
                    "path": btn.sound_path,
                    "label": btn.label_text,
                    "mode": "loop" if btn.is_loop else "one-shot",
                    "volume": btn.button_volume,
                }
            )

        config = {
            "buttons": button_items,
            "global_volume": self.volume,
            "update": {
                "skip_version": self.update_skip_version,
            },
            "app_version": APP_VERSION,
        }

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except OSError as e:
            _dbg(f"Error saving config '{CONFIG_FILE}': {e!r}")

        self.refresh_volumes()

    def load_config(self):
        if not os.path.isfile(CONFIG_FILE):
            _dbg(f"No config file found at '{CONFIG_FILE}', using defaults")
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            _dbg(f"Error loading config '{CONFIG_FILE}': {e!r}")
            return

        items = []
        volume = self.volume
        skip_version: Optional[str] = None

        if isinstance(raw, list):
            _dbg("Config format: legacy list")
            items = raw
            if items and isinstance(items[0], dict):
                first = items[0]
                try:
                    volume = float(first.get("global_volume", first.get("volume", 1.0)))
                except (TypeError, ValueError):
                    volume = 1.0
        elif isinstance(raw, dict):
            _dbg("Config format: dict (new)")
            maybe_buttons = raw.get("buttons", [])
            if isinstance(maybe_buttons, list):
                items = maybe_buttons

            try:
                volume = float(raw.get("global_volume", 1.0))
            except (TypeError, ValueError):
                volume = 1.0

            update_cfg = raw.get("update", {})
            if isinstance(update_cfg, dict):
                value = update_cfg.get("skip_version")
                if isinstance(value, str) and value.strip():
                    skip_version = value.strip()
        else:
            _dbg("Config format: unsupported, ignoring")
            return

        self.volume = max(0.0, min(1.0, volume))
        self.update_skip_version = skip_version

        _dbg(
            f"Config applied: global_volume={self.volume}, "
            f"skip_version={self.update_skip_version}"
        )

        for btn, item in zip(self.buttons, items):
            if not isinstance(item, dict):
                continue

            path = item.get("path")
            label = item.get("label", btn.label_text)
            mode_str = item.get("mode", "one-shot")
            is_loop = mode_str == "loop"
            try:
                btn_volume = float(item.get("volume", 1.0))
            except (TypeError, ValueError):
                btn_volume = 1.0

            if path:
                btn.set_sound(path, label)
            else:
                btn.set_sound(None, label)
            btn.set_mode(is_loop)
            btn.button_volume = max(0.0, min(1.0, btn_volume))

    def closeEvent(self, event):
        try:
            self.save_config()
        except Exception as e:
            _dbg(f"Exception during closeEvent save_config: {e!r}")
        super().closeEvent(event)

    # --- Update integration ---

    def _get_skip_version(self) -> Optional[str]:
        return self.update_skip_version

    def _set_skip_version(self, value: Optional[str]) -> None:
        self.update_skip_version = value
        _dbg(f"_set_skip_version: new skip_version={self.update_skip_version}")
        try:
            self.save_config()
        except Exception as e:
            _dbg(
                "_set_skip_version: error saving config after "
                f"skip_version update: {e!r}"
            )

    def _manual_update_check(self, result_callback=None) -> None:
        _dbg("_manual_update_check: triggered from UI")
        if self._update_client is None:
            _dbg("_manual_update_check: no update client, ignoring")
            if callable(result_callback):
                try:
                    result_callback("error")
                except Exception as cb_e:
                    _dbg(
                        "_manual_update_check: error while calling "
                        f"result_callback without client: {cb_e!r}"
                    )
            return
        try:
            self._update_client.check_now(
                ignore_skip=True,
                result_callback=result_callback,
            )
        except Exception as e:
            _dbg(f"_manual_update_check: exception during check_now: {e!r}")
            if callable(result_callback):
                try:
                    result_callback("error")
                except Exception as cb_e:
                    _dbg(
                        "_manual_update_check: error while calling "
                        f"result_callback after exception: {cb_e!r}"
                    )

    def _setup_update_checker(self):
        if not self._update_os_tag:
            _dbg("_setup_update_checker: OS tag is empty, skipping update check")
            return

        self._update_client = UpdateClient(
            parent_widget=self,
            app_version=APP_VERSION,
            descriptor_url=UPDATE_DESCRIPTOR_URL,
            os_tag=self._update_os_tag,
            get_skip_version=self._get_skip_version,
            set_skip_version=self._set_skip_version,
        )

        self._update_client.start()

    # --- Help window ---

    def _show_help_window(self) -> None:
        if self._help_window is None:
            _dbg("_show_help_window: creating HelpWindow instance")
            self._help_window = HelpWindow(None)

        _dbg("_show_help_window: showing HelpWindow")
        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()
