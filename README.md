# SoundBoard27

Latest releases (Windows / Linux binaries):  
**[Download from the Releases page](https://github.com/Retzilience/SoundBoard27/releases)**

SoundBoard27 is a lightweight 27-button soundboard arranged as three pages of 3×3 buttons (3×9 total). Each slot can be assigned an audio or video file and configured per-button for one-shot or looping playback, with independent per-button volume and a global volume control. The application targets Windows and Linux and is implemented with PySide6/Qt for the UI and QtMultimedia for playback.

![UI](https://github.com/Retzilience/SoundBoard27/raw/assets/assets/ui.png)

## Features

- 27 assignable slots (audio or video files)
- Per-button playback mode: one-shot or loop (toggle on/off)
- Per-button volume multiplier and global volume control
- Three pages of 3×3 buttons for quick access
- Stop controls for one-shots, loops, or everything
- Manual update checking (and optional automatic startup check, depending on build/config)
- Per-user configuration file with stable pathing
- Built-in Help / About window with support links

## Installation

Download the appropriate build from the releases page and extract it. 

Windows:
- Download: `SoundBoard27_win_x.y.zip`
- Run: `SoundBoard27.exe`

Linux:
- Download: `SoundBoard27_linux_x.y.tar.gz`
- Run: `SoundBoard27`
- Notes: playback support depends on QtMultimedia and available system codecs (commonly provided via FFmpeg/GStreamer stacks depending on distribution).

## Usage

Launch SoundBoard27 and open `Load Sounds [Settings...]` to assign files and labels to each slot. The loader provides per-slot mode selection (one-shot vs loop) and per-slot volume control. The main window provides stop controls (`stop one-shot`, `stop loops`, `stop all`) and a global volume slider.

Supported media types include common audio/video formats such as WAV, MP3, OGG, FLAC, MP4, MKV, AVI, and MOV. Actual format support is determined by the QtMultimedia backend and the codecs available on the host system.

Update checks can be triggered manually from the loader window using `Check for Updates`.

## Configuration

Configuration is stored in a per-user directory and includes button assignments (paths, labels, mode, per-button volume), global volume, and update-skip state.

Default locations:
- Linux: `~/.config/SoundBoard27/soundboard_config.json`
- Windows: `%APPDATA%\SoundBoard27\soundboard_config.json`

## Source Code

Repository: https://github.com/Retzilience/SoundBoard27

## License

See `LICENSE` in the repository. The project is non-commercial and open-source. Modified or derived work must remain open-source and include attribution to the original project.
