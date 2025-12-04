# SoundBoard27

SoundBoard27 is a simple 27-button soundboard arranged in a 3×9 grid.  
Each button supports one-shot and loop playback modes, along with per-button volume.  
The application runs on Windows and Linux and uses PySide6/Qt for the interface and multimedia.

## Features

- 27 assignable sound or video slots  
- Loop or one-shot playback per button  
- Per-button volume and global volume  
- Three pages of 3×3 buttons  
- Automatic and manual update checks  
- Config file stored in a per-user directory  
- Basic help/credits window

## Installation

Download the appropriate build from the releases page.

**Windows:**  
`SoundBoard27_win_0.3.zip` → extract and run `SoundBoard27.exe`

**Linux:**  
`SoundBoard27_linux_0.3.tar.gz` → extract and run `SoundBoard27`  
Requires standard desktop environment with Qt/FFmpeg-compatible codecs.

## Usage

Launch the program.  
Press “Load Sounds [Settings…]” to assign files to each button.  
Supported types include WAV, MP3, OGG, FLAC, MP4, MKV, AVI, and MOV.

Loop mode can be enabled per button.  
Volume can be adjusted globally or per button.

The “Check for Updates” button is available inside the load/settings window.

## Configuration

The application stores configuration in a per-user directory:

- Linux: `~/.config/SoundBoard27/soundboard_config.json`  
- Windows: `%APPDATA%\SoundBoard27\soundboard_config.json`

It includes button assignments, volume settings, and update-skip state.

## Source Code

Source code is available on GitHub:

https://github.com/Retzilience/SoundBoard27

## License

See the included `LICENSE` file.  
The project is non-commercial and open-source. Any modified or derived work must also remain open-source and include attribution to the original project.
