"""Build runnable application and Inno Setup installer using the current Python."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "StockPet.spec"], cwd=root, check=True)
compiler = shutil.which("ISCC")
if not compiler:
    for directory in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6",
                      Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6"):
        if (directory / "ISCC.exe").exists():
            compiler = str(directory / "ISCC.exe")
            break
if not compiler:
    raise SystemExit("请安装 Inno Setup 6 后再构建安装包。")
subprocess.run([compiler, "installer.iss"], cwd=root, check=True)
print(root / "dist" / "StockPet-Setup-1.0.0.exe")
