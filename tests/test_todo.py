import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import Qt, QPoint, QDateTime, QTime, QTimer
from PyQt5.QtWidgets import QApplication, QDialogButtonBox
from PyQt5.QtWidgets import QPushButton, QCheckBox
from PyQt5.QtTest import QTest
from todo_dialog import TodoDialog, ReminderTimeDialog


class TodoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def edit_reminder(self, dialog, index, action):
        dialog.show()
        self.app.processEvents()
        task_id = dialog.tasks[index]["id"]
        row = dialog.list.itemWidget(dialog.list.item(index))
        button = row.findChild(QPushButton, "remind_" + task_id)
        errors = []

        def interact():
            editor = self.app.activeModalWidget()
            try:
                self.assertIsInstance(editor, ReminderTimeDialog)
                action(editor)
                self.assertFalse(editor.isVisible(), "Test action must close the picker")
            except BaseException as error:
                errors.append(error)
                if editor:
                    editor.reject()

        QTimer.singleShot(0, interact)
        QTest.mouseClick(button, Qt.LeftButton)
        if errors:
            raise errors[0]

    def choose_future_time(self, editor):
        selected = QDateTime.currentDateTime().addDays(2)
        editor.calendar.setSelectedDate(selected.date())
        editor.time_edit.setTime(QTime(18, 30))
        return QDateTime(selected.date(), QTime(18, 30)).toSecsSinceEpoch()

    def test_row_reminder_select_then_confirm_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            for text in ("第一项", "第二项"):
                d.input.setText(text)
                d.add_task()
            before = path.read_bytes()
            expected = []

            def confirm(editor):
                self.assertEqual(path.read_bytes(), before)
                self.assertIsNone(d.tasks[1]["due"])
                expected.append(self.choose_future_time(editor))
                QTest.mouseClick(editor.save_button, Qt.LeftButton)

            self.edit_reminder(d, 1, confirm)
            self.assertIsNone(d.tasks[0]["due"])
            self.assertEqual(d.tasks[1]["due"], expected[0])
            self.assertFalse(d.tasks[1]["notified"])
            restored = TodoDialog(storage_path=path)
            self.assertEqual(restored.tasks[1]["due"], expected[0])
            d.input.setText("第三项")
            d.add_task()
            self.assertIsNone(d.tasks[2]["due"])
            d.close()
            restored.close()

    def test_existing_reminder_return_and_clear_preserve_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            d.input.setText("已完成事项")
            d.add_task()
            due = QDateTime.currentDateTime().addDays(3)
            d.tasks[0].update(due=due.toSecsSinceEpoch(), done=True, notified=True)
            d._save()
            d._refresh()
            before = path.read_bytes()

            def go_back(editor):
                self.assertEqual(editor.calendar.selectedDate(), due.date())
                self.assertEqual(editor.time_edit.time(), QTime(due.time().hour(), due.time().minute()))
                self.choose_future_time(editor)
                buttons = editor.findChild(QDialogButtonBox)
                QTest.mouseClick(buttons.button(QDialogButtonBox.Cancel), Qt.LeftButton)

            self.edit_reminder(d, 0, go_back)
            self.assertEqual(path.read_bytes(), before)
            self.edit_reminder(d, 0, lambda editor: QTest.mouseClick(editor.clear_button, Qt.LeftButton))
            self.assertIsNone(d.tasks[0]["due"])
            self.assertTrue(d.tasks[0]["done"])
            self.assertFalse(d.tasks[0]["notified"])
            self.assertIsNone(TodoDialog(storage_path=path).tasks[0]["due"])
            d.close()

    def test_past_time_does_not_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            d.input.setText("检查时间")
            d.add_task()
            before = path.read_bytes()

            def invalid(editor):
                editor.calendar.setSelectedDate(QDateTime.currentDateTime().date())
                editor.time_edit.setTime(QTime(0, 0))
                QTest.mouseClick(editor.save_button, Qt.LeftButton)
                self.assertTrue(editor.isVisible())
                self.assertIn("未来", editor.error.text())
                self.assertFalse(editor.error.isHidden())
                editor.reject()

            self.edit_reminder(d, 0, invalid)
            self.assertEqual(path.read_bytes(), before)
            self.assertIsNone(d.tasks[0]["due"])
            d.close()

    def test_reminder_save_failure_preserves_previous_reminder(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            d.input.setText("保留提醒")
            d.add_task()
            old_due = QDateTime.currentSecsSinceEpoch() + 3600
            d.tasks[0].update(due=old_due, notified=True)
            d._save()
            d._refresh()
            before = path.read_bytes()

            def confirm(editor):
                self.choose_future_time(editor)
                QTest.mouseClick(editor.save_button, Qt.LeftButton)

            with patch("todo_dialog.os.replace", side_effect=OSError):
                self.edit_reminder(d, 0, confirm)
            self.assertEqual(d.tasks[0]["due"], old_due)
            self.assertTrue(d.tasks[0]["notified"])
            self.assertEqual(path.read_bytes(), before)
            self.assertIn("保存失败", d.status.text())
            d.close()

    def test_list_refresh_while_picker_open_keeps_correct_task(self):
        with tempfile.TemporaryDirectory() as folder:
            d = TodoDialog(storage_path=Path(folder) / "todos.json")
            for text in ("第一项", "第二项"):
                d.input.setText(text)
                d.add_task()
            expected = []

            def confirm(editor):
                d._refresh()
                expected.append(self.choose_future_time(editor))
                QTest.mouseClick(editor.save_button, Qt.LeftButton)

            self.edit_reminder(d, 1, confirm)
            self.assertIsNone(d.tasks[0]["due"])
            self.assertEqual(d.tasks[1]["due"], expected[0])
            d.close()

    def test_add_complete_reopen_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            d.input.setText("  喝水  ")
            d.add_task()
            d.input.setText("   ")
            d.add_task()
            self.assertEqual(d.list.count(), 1)
            d.list.item(0).setCheckState(Qt.Checked)
            restored = TodoDialog(storage_path=path)
            self.assertEqual(restored.list.item(0).text(), "喝水")
            self.assertEqual(restored.list.item(0).checkState(), Qt.Checked)
            self.assertTrue(restored.list.item(0).font().strikeOut())
            restored.list.setCurrentRow(0)
            restored.delete_selected()
            self.assertEqual(TodoDialog(storage_path=path).list.count(), 0)
            d.close()
            restored.close()

    def test_save_failure_preserves_input_and_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            d.input.setText("原待办")
            d.add_task()
            before = path.read_bytes()
            d.input.setText("新增待办")
            with patch("todo_dialog.os.replace", side_effect=OSError):
                d.add_task()
            self.assertEqual(d.input.text(), "新增待办")
            self.assertEqual(len(d.tasks), 1)
            self.assertEqual(path.read_bytes(), before)
            self.assertIn("保存失败", d.status.text())
            d.close()

    def test_row_delete_works_without_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "todos.json"
            d = TodoDialog(storage_path=path)
            for text in ("保留事项", "删除事项"):
                d.input.setText(text)
                d.add_task()
            d.show()
            self.app.processEvents()
            row = d.list.itemWidget(d.list.item(1))
            checkbox = row.findChild(QCheckBox)
            QTest.mouseClick(checkbox, Qt.LeftButton, pos=QPoint(8, checkbox.height() // 2))
            self.assertTrue(d.tasks[1]["done"])
            d.list.clearSelection()
            delete = row.findChild(QPushButton, "delete_" + d.tasks[1]["id"])
            QTest.mouseClick(delete, Qt.LeftButton)
            self.assertEqual([t["text"] for t in d.tasks], ["保留事项"])
            restored = TodoDialog(storage_path=path)
            self.assertEqual(restored.list.count(), 1)
            d.close()
            restored.close()
