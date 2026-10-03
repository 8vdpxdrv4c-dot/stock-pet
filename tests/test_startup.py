import unittest
from unittest.mock import patch, MagicMock
import startup


class StartupTests(unittest.TestCase):
    def test_frozen_command_and_registry_toggle(self):
        with patch.object(startup.sys, "frozen", True, create=True), patch.object(startup.sys, "executable", r"C:\Pet App\StockPet.exe"):
            self.assertEqual(startup.startup_command(), '"C:\\Pet App\\StockPet.exe"')
            with patch.object(startup.winreg, "CreateKey") as key, patch.object(startup.winreg, "SetValueEx") as write:
                startup.set_enabled(True)
                write.assert_called_once_with(key.return_value.__enter__.return_value, "StockPet", 0, startup.winreg.REG_SZ, '"C:\\Pet App\\StockPet.exe"')
        with patch.object(startup.winreg, "CreateKey"), patch.object(startup.winreg, "DeleteValue") as delete:
            startup.set_enabled(False)
            delete.assert_called_once()

    def test_missing_startup_is_disabled(self):
        with patch.object(startup.winreg, "OpenKey", side_effect=FileNotFoundError):
            self.assertFalse(startup.is_enabled())
