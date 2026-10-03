import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from todo_dialog import TodoDialog
from reminder_manager import ReminderManager


class ReminderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.todo = TodoDialog(storage_path=Path(self.temp.name) / "tasks.json")
        self.owner = SimpleNamespace(pet=self.todo, todo=self.todo, speech=MagicMock(), _busy_walk=False)
        self.manager = ReminderManager(self.owner, {"quiet_mode": {"fullscreen": False}})
        self.manager.timer.stop()

    def tearDown(self):
        self.manager.stop()
        self.todo.close()
        self.temp.cleanup()

    def add_due_task(self):
        self.todo.input.setText("喝水")
        self.todo.add_task()
        self.todo.tasks[0]["due"] = time.time() - 1
        self.todo._save()

    def test_due_is_deferred_and_reminded_once_after_focus(self):
        self.add_due_task()
        self.manager.set_focus(True)
        self.manager.tick()
        self.owner.speech.say_once.assert_not_called()
        self.assertFalse(self.todo.tasks[0]["notified"])
        self.manager.set_focus(False)
        self.assertTrue(self.todo.tasks[0]["notified"])
        self.owner.speech.say_once.assert_called_once()
        self.manager.next_display = 0
        self.manager.tick()
        self.owner.speech.say_once.assert_called_once()
        restored = TodoDialog(storage_path=self.todo.path)
        self.assertEqual(restored.due_tasks(time.time()), [])
        restored.close()

    def test_fullscreen_defer_and_cancelled_task_not_sent(self):
        self.add_due_task()
        self.manager.auto_quiet = True
        with patch("reminder_manager.foreground_fullscreen", return_value=True):
            self.manager.tick()
            self.owner.speech.say_once.assert_not_called()
            self.todo.list.item(0).setCheckState(Qt.Checked)
        with patch("reminder_manager.foreground_fullscreen", return_value=False):
            self.manager.tick()
            self.owner.speech.say_once.assert_not_called()

    def test_sedentary_snooze_and_disable(self):
        self.manager.rest_due = time.time() - 1
        self.manager.tick()
        self.assertTrue(self.manager.rest_dialog.isVisible())
        self.manager.rest_dialog.finish(5)
        self.assertFalse(self.manager.rest_dialog.isVisible())
        self.assertAlmostEqual(self.manager.rest_due - time.time(), 300, delta=2)
        self.manager.configure({"wellness": {"enabled": False}})
        self.manager.rest_due = time.time() - 1
        self.manager.next_display = 0
        self.manager.tick()
        self.assertFalse(self.manager.rest_dialog.isVisible())
