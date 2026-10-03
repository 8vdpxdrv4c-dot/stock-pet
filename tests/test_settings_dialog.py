"""Restored settings must round-trip without losing unrelated configuration."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication, QGroupBox

import config
from settings_dialog import SettingsDialog


class SettingsRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "config.json"
        self.original = {
            "pet_name": "花花", "pet_scale_percent": 70,
            "deepseek_api_key": "stored elsewhere", "deepseek_base_url": "https://example.invalid",
            "deepseek_model": "custom-model", "system_prompt": "你叫{pet_name}，保持原风格。",
            "check_interval_minutes": 7,
            "discipline": {"legacy": True},
            "speech_reminder": {"enabled": True, "interval_minutes": 30, "text": "休息一下", "custom": "keep"},
            "wellness": {"enabled": False, "interval_minutes": 75},
            "quiet_mode": {"fullscreen": False, "custom": "keep"}, "other": {"preserve": True},
        }
        self.path.write_text(json.dumps(self.original, ensure_ascii=False), encoding="utf-8")
        self.config_patch = patch.object(config, "CONFIG_PATH", str(self.path))
        self.config_patch.start()
        self.key_patch = patch.object(config.credential_store, "get_api_key", return_value="existing-test-key")
        self.key_patch.start()
        self.startup_patch = patch("settings_dialog.startup.is_enabled", return_value=False)
        self.startup_patch.start()
        self.dialog = SettingsDialog(config.load_config())

    def tearDown(self):
        self.dialog.close()
        self.startup_patch.stop()
        self.key_patch.stop()
        self.config_patch.stop()
        self.temp.cleanup()

    def test_all_original_sections_load_and_cancel_preserves_config(self):
        group_titles = [box.title() for box in self.dialog.findChildren(QGroupBox)]
        self.assertNotIn("交易纪律", group_titles)
        self.assertIn("喝水 / 自定义提醒", group_titles)
        self.assertIn("久坐休息提醒", group_titles)
        self.assertEqual(self.dialog.model_edit.text(), "custom-model")
        self.assertEqual(self.dialog.scale_spin.value(), 70)
        self.assertEqual(self.dialog.speech_interval_spin.value(), 30)
        self.assertEqual(self.dialog.speech_text_edit.text(), "休息一下")
        self.assertEqual(self.dialog.wellness_interval_spin.value(), 75)
        self.assertFalse(self.dialog.wellness_box.isChecked())
        self.assertFalse(self.dialog.fullscreen_check.isChecked())
        self.assertEqual(self.dialog.prompt_edit.toPlainText(), self.original["system_prompt"])
        self.dialog.pet_name_edit.setText("未保存的名字")
        self.dialog.reject()
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), self.original)

    def test_save_name_preserves_prompt_template_unknown_fields_and_key(self):
        self.dialog.pet_name_edit.setText("小橘")
        self.dialog.key_edit.clear()
        emitted = []
        self.dialog.saved.connect(emitted.append)
        with patch.object(config, "save_api_key") as save_key, patch("settings_dialog.startup.set_enabled") as startup:
            self.dialog._on_save()
        save_key.assert_not_called()
        startup.assert_not_called()
        restored = json.loads(self.path.read_text(encoding="utf-8"))
        expected = deepcopy(self.original)
        expected["pet_name"] = "小橘"
        expected["deepseek_api_key"] = "（已存到系统凭据管理器）"
        expected.pop("discipline")
        expected.pop("check_interval_minutes")
        self.assertEqual(restored, expected)
        self.assertEqual(emitted[0]["deepseek_api_key"], "existing-test-key")
        self.assertEqual(emitted[0]["system_prompt"], "你叫小橘，保持原风格。")
        self.assertEqual(config.load_config()["_system_prompt_template"], self.original["system_prompt"])

    def test_restored_fields_save_and_preview_signal_reaches_consumer(self):
        self.dialog.scale_spin.setValue(120)
        self.dialog.prompt_edit.setPlainText("你是{pet_name}，用简洁中文回答。")
        self.dialog.speech_interval_spin.setValue(15)
        self.dialog.wellness_box.setChecked(True)
        self.dialog.fullscreen_check.setChecked(True)
        self.dialog.startup_check.setChecked(True)
        previewed = []
        self.dialog.speech_preview.connect(previewed.append)
        self.dialog.speech_preview.emit("预览测试")
        self.assertEqual(previewed, ["预览测试"])
        with patch("settings_dialog.startup.set_enabled") as startup:
            self.dialog._on_save()
        startup.assert_called_once_with(True)
        restored = config.load_config()
        self.assertEqual(restored["pet_scale_percent"], 120)
        self.assertEqual(restored["speech_reminder"]["interval_minutes"], 15)
        self.assertTrue(restored["wellness"]["enabled"])
        self.assertTrue(restored["quiet_mode"]["fullscreen"])
        self.assertEqual(restored["system_prompt"], "你是花花，用简洁中文回答。")

    def test_invalid_prompt_does_not_write_config_credentials_or_startup(self):
        self.dialog.prompt_edit.setPlainText("错误的占位符：{unknown}")
        self.dialog.key_edit.setText("new-test-key")
        self.dialog.startup_check.setChecked(True)
        with patch("settings_dialog.QMessageBox.critical") as warning, \
             patch.object(config, "save_api_key") as key, patch("settings_dialog.startup.set_enabled") as startup:
            self.dialog._on_save()
        warning.assert_called_once()
        key.assert_not_called()
        startup.assert_not_called()
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), self.original)
