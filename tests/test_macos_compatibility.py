"""Protect Mac startup, writable storage, and the native-build boundary."""
import os
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths
import build_macos
import startup


class MacCompatibilityTests(unittest.TestCase):
    def test_mac_data_ignores_windows_appdata(self):
        with patch.object(app_paths.sys, "platform", "darwin"), \
             patch.dict(os.environ, {"APPDATA": "C:/WindowsUserData"}):
            self.assertEqual(app_paths.user_data_dir(),
                             Path.home() / "Library/Application Support/StockPet")

    def test_mac_login_agent_uses_argument_array_and_can_be_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "LaunchAgents/com.stockpet.desktop.plist"
            executable = "/Applications/Stock Pet.app/Contents/MacOS/StockPet"
            with patch.object(startup.sys, "platform", "darwin"), \
                 patch.object(startup.sys, "frozen", True, create=True), \
                 patch.object(startup.sys, "executable", executable), \
                 patch.object(startup, "_launch_agent_path", return_value=path):
                self.assertFalse(startup.is_enabled())
                startup.set_enabled(True)
                data = plistlib.loads(path.read_bytes())
                self.assertEqual(data["ProgramArguments"], [executable])
                self.assertTrue(data["RunAtLoad"])
                self.assertTrue(startup.is_enabled())
                startup.set_enabled(False)
                self.assertFalse(startup.is_enabled())

    def test_windows_cannot_silently_produce_a_fake_mac_app(self):
        with patch.object(build_macos.sys, "platform", "win32"), \
             patch.object(build_macos, "run_logged") as run:
            self.assertEqual(build_macos.main([]), 1)
            run.assert_not_called()

    def test_mac_entrypoint_does_not_import_windows_modules(self):
        import subprocess
        import sys
        script = '''
import sys, importlib.abc
sys.platform = "darwin"
class RejectWindows(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ("winreg", "win_recycle"):
            raise AssertionError("Windows-only import: " + fullname)
sys.meta_path.insert(0, RejectWindows())
import main
assert main.win_recycle is None
'''
        # Simulate the platform after loading the actual host's native Qt modules.
        script = "import PyQt5.QtWidgets, openai, jieba, keyring\n" + script
        result = subprocess.run([sys.executable, "-c", script],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
