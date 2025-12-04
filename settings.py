import sys
import os
import shutil
from pathlib import Path

APP_NAME = "GambitBoard"
CONFIG_BASENAME = "soundboard_config.json"

# Pastel accent colors
ONE_SHOT_COLOR = "#ff8a65"         # warm pastel orange for one-shot
ONE_SHOT_COLOR_SOFT = "#ffccbc"    # lighter variant for pulse
LOOP_COLOR = "#00ffff"             # aqua for loops


def resolve_config_path() -> str:
    """
    Resolve the configuration path in a per-user location and, if a legacy
    config file exists in the application directory, copy it over once.

    On Linux:  ~/.config/GambitBoard/soundboard_config.json
    On Windows: %APPDATA%\\GambitBoard\\soundboard_config.json

    If creating the directory or copying fails, fall back to the legacy
    location so existing behaviour is preserved.
    """
    home = Path.home()

    if sys.platform.startswith("win"):
        base_dir = Path(os.environ.get("APPDATA", home))
        config_dir = base_dir / APP_NAME
    else:
        # Linux and other Unix-like systems
        config_dir = home / ".config" / APP_NAME

    legacy_path = Path(os.path.abspath(os.path.dirname(sys.argv[0]))) / CONFIG_BASENAME

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # If we cannot create the config directory, just keep using legacy file
        return str(legacy_path)

    new_path = config_dir / CONFIG_BASENAME

    if legacy_path.is_file() and not new_path.is_file():
        try:
            shutil.copy2(legacy_path, new_path)
        except OSError:
            # Copy failed, keep using legacy
            return str(legacy_path)

    return str(new_path)


CONFIG_FILE = resolve_config_path()
