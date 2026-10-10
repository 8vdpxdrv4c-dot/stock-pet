"""Writable user data location, independent of the application bundle."""
import os
import sys
from pathlib import Path


def user_data_dir():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/StockPet"
    return Path(os.environ.get("APPDATA", str(Path.home() / ".local/share"))) / "StockPet"
