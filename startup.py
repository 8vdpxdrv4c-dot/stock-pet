"""Per-user Windows startup setting (no administrator permissions required)."""
import os
import subprocess
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "StockPet"


def startup_command():
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([sys.executable])
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return subprocess.list2cmdline([pythonw, os.path.join(os.path.dirname(__file__), "main.py")])


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(command)
    except FileNotFoundError:
        return False


def set_enabled(enabled):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
