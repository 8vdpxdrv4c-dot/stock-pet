"""Per-user login startup for Windows and macOS."""
import os
import subprocess
import sys
import plistlib
from pathlib import Path

if sys.platform == "win32":
    import winreg
else:
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "StockPet"
MAC_LABEL = "com.stockpet.desktop"


def is_supported():
    return sys.platform in ("win32", "darwin")


def _launch_agent_path():
    return Path.home() / "Library/LaunchAgents" / (MAC_LABEL + ".plist")


def _mac_arguments():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(Path(__file__).resolve().with_name("main.py"))]


def startup_command():
    if sys.platform == "darwin":
        import shlex
        return shlex.join(_mac_arguments())
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([sys.executable])
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return subprocess.list2cmdline([pythonw, os.path.join(os.path.dirname(__file__), "main.py")])


def is_enabled():
    if sys.platform == "darwin":
        return _launch_agent_path().is_file()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(command)
    except FileNotFoundError:
        return False


def set_enabled(enabled):
    if sys.platform == "darwin":
        path = _launch_agent_path()
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {"Label": MAC_LABEL, "ProgramArguments": _mac_arguments(),
                    "RunAtLoad": True, "ProcessType": "Interactive"}
            temporary = path.with_suffix(".plist.tmp")
            with temporary.open("wb") as stream:
                plistlib.dump(data, stream)
            temporary.replace(path)
        else:
            path.unlink(missing_ok=True)
        return
    if winreg is None:
        raise RuntimeError("当前系统不支持自动启动设置。")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
