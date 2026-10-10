"""Keep startup errors visible in a log for windowed builds."""
import os
import sys
from pathlib import Path

folder = Path(os.environ.get("APPDATA", str(Path.home()))) / "StockPet"
if sys.platform == "darwin":
    folder = Path.home() / "Library/Application Support/StockPet"
folder.mkdir(parents=True, exist_ok=True)
stream = (folder / "app.log").open("a", encoding="utf-8", buffering=1)
sys.stdout = stream
sys.stderr = stream
print("Starting StockPet")
