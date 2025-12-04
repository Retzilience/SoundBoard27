from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QFileDialog, QScrollArea, QLineEdit,
    QRadioButton, QButtonGroup, QSlider
)

from settings import ONE_SHOT_COLOR, ONE_SHOT_COLOR_SOFT, LOOP_COLOR


class SoundButton(QPushButton):
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.sound_path = None
        self.label_text = f"Button {index + 1}"
        self.setText(self.label_text)
        self.setMinimumSize(QSize(150, 100))

        # Playback mode: False = one-shot, True = loop
        self.is_loop = False
        self.is_playing = False

        # Per-button volume (0.0–1.0), multiplied by global volume
        self.button_volume = 1.0

        # Visual styles
        # One-shot base (dark with subtle outline)
        self.default_style = (
            "background-color: #252525;"
            "color: #ffffff;"
            "border: 2px solid #555555;"
        )

        # One-shot active pulse styles (outline only)
        self.one_shot_active_style1 = (
            f"background-color: #252525; color: #ffffff; border: 2px solid {ONE_SHOT_COLOR};"
        )
        self.one_shot_active_style2 = (
            f"background-color: #252525; color: #ffffff; border: 2px solid {ONE_SHOT_COLOR_SOFT};"
        )

        # Loop visuals: dark cyan when idle, pulsating grey-green when active
        self.loop_inactive_style = (
            "background-color: #005f5f; color: #ffffff; border: 2px solid #003f3f;"
        )
        self.loop_active_style1 = (
            "background-color: #3a5f46; color: #ffffff; border: 2px solid #4caf50;"
        )
        self.loop_active_style2 = (
            "background-color: #2f4f3c; color: #ffffff; border: 2px solid #66bb6a;"
        )

        # Disabled / unloaded style
        self.disabled_style = (
            "background-color: #202020;"
            "color: #666666;"
            "border: 1px dashed #444444;"
        )

        self._pulse_state = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(500)
        self._pulse_timer.timeout.connect(self._on_pulse_timeout)

        # Start in "unloaded" state
        self.setEnabled(False)
        self.update_style()

    def set_sound(self, path, label):
        self.sound_path = path or None
        self.label_text = label
        self.setText(label)
        self.update_enabled_state()

    def update_enabled_state(self):
        has_sound = bool(self.sound_path)
        self.setEnabled(has_sound)
        if not has_sound:
            # Ensure we are visually and logically idle
            self.is_playing = False
            if self._pulse_timer.isActive():
                self._pulse_timer.stop()
                self._pulse_state = False
        self.update_style()

    def set_mode(self, is_loop):
        self.is_loop = bool(is_loop)
        self.update_style()

    def set_playing(self, active):
        active = bool(active) and bool(self.sound_path)
        self.is_playing = active

        if self.is_playing:
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            if self._pulse_timer.isActive():
                self._pulse_timer.stop()
                self._pulse_state = False

        self.update_style()

    def highlight(self, active):
        # Backwards-compatible wrapper
        self.set_playing(active)

    def _on_pulse_timeout(self):
        self._pulse_state = not self._pulse_state
        self.update_style()

    def update_style(self):
        if not self.sound_path:
            style = self.disabled_style
        else:
            if self.is_loop:
                if self.is_playing:
                    style = self.loop_active_style1 if self._pulse_state else self.loop_active_style2
                else:
                    style = self.loop_inactive_style
            else:
                if self.is_playing:
                    style = self.one_shot_active_style1 if self._pulse_state else self.one_shot_active_style2
                else:
                    style = self.default_style
        self.setStyleSheet(style)


class LoadWindow(QWidget):
    def __init__(self, buttons, save_callback, parent=None):
        super().__init__(None)  # Force top-level window
        self.buttons = buttons
        self.save_callback = save_callback

        self.setWindowTitle("Load Sounds")
        self.setMinimumSize(800, 500)

        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(8)

        # Header row aligned with the columns
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(5)

        index_header = QLabel("#")
        index_header.setFixedWidth(30)

        load_header = QLabel("")
        load_header.setFixedWidth(60)

        path_header = QLabel("Path")
        path_header.setMinimumWidth(300)

        label_header = QLabel("Label")
        label_header.setMinimumWidth(150)

        vol_header = QLabel("vol.")
        vol_header.setFixedWidth(110)

        mode_header = QLabel(
            f'<span style="color:{ONE_SHOT_COLOR};">● one-shot</span>'
            '&nbsp;&nbsp;'
            f'<span style="color:{LOOP_COLOR};">● loop</span>'
        )
        mode_header.setTextFormat(Qt.RichText)
        mode_header.setMinimumWidth(130)

        header_row.addWidget(index_header)
        header_row.addWidget(load_header)
        header_row.addWidget(path_header, 1)
        header_row.addWidget(label_header, 1)
        header_row.addWidget(vol_header)
        header_row.addWidget(mode_header)

        container_layout.addLayout(header_row)

        for i, btn in enumerate(self.buttons):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(5)

            index_label = QLabel(str(i + 1))
            index_label.setFixedWidth(30)

            load_button = QPushButton("Load")
            load_button.setFixedWidth(60)
            load_button.clicked.connect(lambda _, b=btn: self.load_file(b))

            path_field = QLineEdit(btn.sound_path if btn.sound_path else "")
            path_field.setReadOnly(True)
            path_field.setMinimumWidth(300)

            label_field = QLineEdit(btn.label_text)
            label_field.setMinimumWidth(150)

            # Per-button volume slider
            vol_container = QWidget()
            vol_layout = QHBoxLayout(vol_container)
            vol_layout.setContentsMargins(0, 0, 0, 0)
            vol_layout.setSpacing(3)

            vol_label = QLabel("vol.")
            vol_slider = QSlider(Qt.Horizontal)
            vol_slider.setRange(0, 100)
            vol_slider.setSingleStep(5)
            vol_slider.setFixedWidth(80)
            vol_slider.setValue(int(btn.button_volume * 100))

            vol_layout.addWidget(vol_label)
            vol_layout.addWidget(vol_slider)
            vol_container.setFixedWidth(110)

            # Per-button mode selectors
            mode_container = QWidget()
            mode_layout = QHBoxLayout(mode_container)
            mode_layout.setContentsMargins(0, 0, 0, 0)
            mode_layout.setSpacing(3)

            one_shot_radio = QRadioButton()
            loop_radio = QRadioButton()

            # Style radios so checked dot matches legend colors
            one_shot_radio.setStyleSheet(f"""
                QRadioButton::indicator {{
                    width: 14px;
                    height: 14px;
                    border-radius: 7px;
                    border: 1px solid #777777;
                    background-color: #202020;
                }}
                QRadioButton::indicator:checked {{
                    border: 1px solid {ONE_SHOT_COLOR};
                    background-color: {ONE_SHOT_COLOR};
                }}
            """)
            loop_radio.setStyleSheet(f"""
                QRadioButton::indicator {{
                    width: 14px;
                    height: 14px;
                    border-radius: 7px;
                    border: 1px solid #777777;
                    background-color: #202020;
                }}
                QRadioButton::indicator:checked {{
                    border: 1px solid {LOOP_COLOR};
                    background-color: {LOOP_COLOR};
                }}
            """)

            mode_group = QButtonGroup(mode_container)
            mode_group.setExclusive(True)
            mode_group.addButton(one_shot_radio)
            mode_group.addButton(loop_radio)

            if btn.is_loop:
                loop_radio.setChecked(True)
            else:
                one_shot_radio.setChecked(True)

            mode_layout.addWidget(one_shot_radio)
            mode_layout.addWidget(loop_radio)
            mode_container.setFixedWidth(70)

            # Attach fields to button for later retrieval
            btn._path_field = path_field
            btn._label_field = label_field
            btn._volume_slider = vol_slider
            btn._one_shot_radio = one_shot_radio
            btn._loop_radio = loop_radio
            btn._mode_group = mode_group

            row.addWidget(index_label)
            row.addWidget(load_button)
            row.addWidget(path_field, 1)
            row.addWidget(label_field, 1)
            row.addWidget(vol_container)
            row.addWidget(mode_container)

            container_layout.addLayout(row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        save_button = QPushButton("Save")
        save_button.setFixedHeight(40)
        save_button.clicked.connect(self.apply_and_save)
        main_layout.addWidget(save_button)

        self.setLayout(main_layout)

    def load_file(self, btn):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sound or Video",
            "",
            "Audio/Video Files (*.wav *.mp3 *.ogg *.flac *.mp4 *.mkv *.avi *.mov)"
        )
        if path:
            btn._path_field.setText(path)

    def apply_and_save(self):
        for btn in self.buttons:
            path = btn._path_field.text().strip()
            label = btn._label_field.text().strip() or f"Button {btn.index + 1}"

            if path:
                btn.set_sound(path, label)
            else:
                # Clear any existing sound assignment
                btn.set_sound(None, label)

            is_loop = False
            if hasattr(btn, "_loop_radio") and btn._loop_radio.isChecked():
                is_loop = True
            btn.set_mode(is_loop)

            if hasattr(btn, "_volume_slider"):
                btn.button_volume = btn._volume_slider.value() / 100.0

        self.save_callback()
        self.close()
