from pathlib import Path
import platform
import os

# Hotkey configuration
HOTKEY_MAP = {
    "record_toggle": "F9",
    "play_toggle": "F10",
}

# Keys ignored by the Recorder to prevent capturing its own hotkeys
IGNORE_KEYS = {k.lower() for k in HOTKEY_MAP.values()}

# Table column indices
COL_IDX = 0
COL_TYPE = 1
COL_TIME = 2
COL_DETAILS = 3
COL_COMMENT = 4


def _get_appdata_dir() -> Path:
    """Return the platform-specific AppData directory for PyCorder."""
    sysname = platform.system()
    if sysname == "Windows":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "PyCorder"
    elif sysname == "Darwin":
        return Path.home() / "Library" / "Application Support" / "PyCorder"
    else:  # Linux / Unix
        return Path.home() / ".config" / "PyCorder"


APPDATA_DIR = _get_appdata_dir()
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

# Autosave location
AUTOSAVE_PATH = APPDATA_DIR / "autosave.json"
