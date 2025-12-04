import os
import json

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QSlider
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from settings import CONFIG_FILE
from widgets import SoundButton, LoadWindow


class Soundboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GambitBoard")

        # One-shot player
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)

        # Loop players per button
        self.loop_players = {}

        self.current_button = None
        self.current_page = 0
        self.volume = 1.0  # global volume 0.0–1.0

        self.buttons = [SoundButton(i) for i in range(27)]
        for btn in self.buttons:
            btn.clicked.connect(lambda _, b=btn: self.play_sound(b))

        self.load_config()

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

        bottom_button = QPushButton("Load sounds")
        bottom_button.clicked.connect(self.open_loader)

        bottom_bar.addWidget(bottom_button)

        # Stop controls
        stop_one_shot_button = QPushButton("stop one-shot")
        stop_loops_button = QPushButton("stop loops")
        stop_all_button = QPushButton("stop all")

        stop_one_shot_button.clicked.connect(self.stop_one_shots)
        stop_loops_button.clicked.connect(self.stop_loops)
        stop_all_button.clicked.connect(self.stop_all)

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

    def open_loader(self):
        loader = LoadWindow(self.buttons, self.save_config, self)
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

    def save_config(self):
        data = []
        for btn in self.buttons:
            data.append({
                "path": btn.sound_path,
                "label": btn.label_text,
                "mode": "loop" if btn.is_loop else "one-shot",
                "volume": btn.button_volume,
            })

        # Store global volume on the first item for backward compatibility
        if data:
            data[0]["global_volume"] = self.volume

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self.refresh_volumes()

    def load_config(self):
        if not os.path.isfile(CONFIG_FILE):
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                items = json.load(f)
            except json.JSONDecodeError:
                return

        if not isinstance(items, list):
            return

        if items and isinstance(items[0], dict):
            first = items[0]
            try:
                # Old configs: no global_volume, only per-button "volume" used as global
                self.volume = float(first.get("global_volume", first.get("volume", 1.0)))
            except (TypeError, ValueError):
                self.volume = 1.0

        for btn, item in zip(self.buttons, items):
            if not isinstance(item, dict):
                continue

            path = item.get("path")
            label = item.get("label", btn.label_text)
            mode_str = item.get("mode", "one-shot")
            is_loop = (mode_str == "loop")
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
        # Optional: auto-save on close
        try:
            self.save_config()
        except Exception:
            pass
        super().closeEvent(event)
