"""Explicit INI storage: the Windows registry is not required."""
import os
from pathlib import Path
from PySide6.QtCore import QSettings
from .engine import APP_DIR


def load_settings():
    explicit = os.environ.get("ZESTE_CONFIG_DIR")
    root = Path(explicit) if explicit else Path(os.environ.get("LOCALAPPDATA", str(APP_DIR))) / "Zeste"
    try: root.mkdir(parents=True, exist_ok=True)
    except OSError:
        if explicit: raise
        root = APP_DIR / "user-data"
        root.mkdir(parents=True, exist_ok=True)
    settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
    settings.setFallbacksEnabled(False)
    return settings
