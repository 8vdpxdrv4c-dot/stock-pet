import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

import config
from config import DEFAULT_SPEECH_TEXT
from pet_widget import PetWidget
from settings_dialog import SettingsDialog
from speech_bubble import SpeechReminder


class SpeechTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.pet = PetWidget()
        self.pet.show()
        self.speech = SpeechReminder(self.pet, {})

    def tearDown(self):
        self.speech.stop()
        self.pet.close()

    def test_default_timer_preview_and_auto_hide(self):
        self.assertTrue(self.speech.timer.isActive())
        self.assertEqual(self.speech.timer.interval(), 5 * 60 * 1000)
        bubble = self.speech.bubble
        self.speech.timer.start(20)
        for _ in range(50):
            QTest.qWait(20)
            if bubble.isVisible():
                break
        self.speech.timer.stop()
        self.assertTrue(bubble.isVisible())
        self.assertEqual(bubble.label.text(), DEFAULT_SPEECH_TEXT)
        self.assertEqual(bubble.label.textFormat(), Qt.PlainText)
        bubble.speak("test", duration_ms=20)
        for _ in range(50):
            QTest.qWait(10)
            if not bubble.isVisible():
                break
        self.assertFalse(bubble.isVisible())
        self.speech.configure({"speech_reminder": {"enabled": False}})
        self.assertFalse(self.speech.timer.isActive())

    def test_bubble_follows_moving_and_resized_pet_within_screen(self):
        self.speech.say_once()
        bounds = self.app.primaryScreen().availableGeometry()
        for corner in (bounds.topLeft(), bounds.bottomRight() - QPoint(180, 160)):
            self.pet.move(corner)
            self.app.processEvents()
            self.assertTrue(bounds.contains(self.speech.bubble.frameGeometry()))
        self.pet.set_scale_percent(200)
        self.app.processEvents()
        self.assertTrue(bounds.contains(self.speech.bubble.frameGeometry()))
        self.pet.hide()
        self.assertFalse(self.speech.bubble.isVisible())

    def test_settings_persist_custom_interval_text_and_disable(self):
        dialog = SettingsDialog({"deepseek_api_key": "test-key"})
        self.assertTrue(dialog.speech_box.isChecked())
        self.assertEqual(dialog.speech_interval_spin.value(), 5)
        self.assertEqual(dialog.speech_text_edit.text(), DEFAULT_SPEECH_TEXT)
        preview = []
        dialog.speech_preview.connect(preview.append)
        dialog.speech_text_edit.setText("记得休息")
        dialog.speech_interval_spin.setValue(12)
        dialog.speech_box.setChecked(False)
        saved = []
        dialog.saved.connect(saved.append)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({"system_prompt": "test"}), encoding="utf-8")
            with patch.object(config, "CONFIG_PATH", str(path)), patch.object(config, "save_api_key"), patch.object(config.credential_store, "get_api_key", return_value=""):
                dialog._on_save()
                restored = config.load_config()
        self.assertEqual(restored["speech_reminder"], {"enabled": False, "interval_minutes": 12, "text": "记得休息"})
        self.speech.configure(saved[0])
        self.assertFalse(self.speech.timer.isActive())
        self.speech.say_once("预览")
        self.assertEqual(self.speech.bubble.label.text(), "预览")


if __name__ == "__main__":
    unittest.main()
