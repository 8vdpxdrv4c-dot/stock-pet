"""本地待办列表，原子保存并支持完成和删除。"""
import json
import os
import uuid
from pathlib import Path

from PyQt5.QtCore import Qt, QStandardPaths, QDateTime, QTime, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                            QPushButton, QListWidget, QListWidgetItem, QLabel,
                            QWidget, QCheckBox, QCalendarWidget, QTimeEdit,
                            QDialogButtonBox, QStyledItemDelegate, QSizePolicy)


class ReminderTimeDialog(QDialog):
    """Choose a task reminder first, then explicitly save or remove it."""

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置提醒")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(380)
        self.reminder_due = None
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        title = QLabel(task["text"])
        title.setTextFormat(Qt.PlainText)
        title.setWordWrap(True)
        layout.addWidget(title)
        existing = task.get("due")
        now = QDateTime.currentDateTime()
        selected = (QDateTime.fromSecsSinceEpoch(int(existing))
                    if isinstance(existing, (int, float)) and existing > now.toSecsSinceEpoch()
                    else now.addSecs(3600))
        self.calendar = QCalendarWidget()
        self.calendar.setMinimumDate(now.date())
        self.calendar.setSelectedDate(selected.date())
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("提醒时间"))
        self.time_edit = QTimeEdit(QTime(selected.time().hour(), selected.time().minute()))
        self.time_edit.setDisplayFormat("HH:mm")
        time_row.addWidget(self.time_edit, 1)
        layout.addLayout(time_row)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color:#b54032;")
        self.error.hide()
        layout.addWidget(self.error)
        if task.get("done"):
            note = QLabel("事项已完成，取消完成后才会触发提醒。")
            note.setWordWrap(True)
            layout.addWidget(note)
        if isinstance(existing, (int, float)):
            current = QLabel("当前提醒：" + QDateTime.fromSecsSinceEpoch(int(existing)).toString("yyyy-MM-dd HH:mm"))
            layout.addWidget(current)
            self.clear_button = QPushButton("取消当前提醒")
            self.clear_button.setAutoDefault(False)
            self.clear_button.clicked.connect(self._clear)
            layout.addWidget(self.clear_button)
        else:
            self.clear_button = None
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.save_button.setText("确认设置")
        buttons.button(QDialogButtonBox.Cancel).setText("返回")
        buttons.accepted.connect(self._confirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _confirm(self):
        due = QDateTime(self.calendar.selectedDate(), self.time_edit.time()).toSecsSinceEpoch()
        if due <= QDateTime.currentSecsSinceEpoch():
            self.error.setText("请选择未来的提醒时间。")
            self.error.show()
            return
        self.reminder_due = due
        self.accept()

    def _clear(self):
        self.reminder_due = None
        self.accept()


class TodoRowDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # The row widget draws its own checkbox and text.
        pass


class TodoDialog(QDialog):
    task_completed = pyqtSignal(str)
    def __init__(self, pet=None, storage_path=None):
        super().__init__(pet)
        self.setWindowTitle("待办")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.resize(520, 480)
        self.path = Path(storage_path) if storage_path else Path(
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)) / "StockPet" / "todos.json"
        self.tasks = []
        self._loading = False
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("添加一件要做的事…")
        self.input.setMaxLength(200)
        row.addWidget(self.input)
        self.add_button = QPushButton("添加")
        row.addWidget(self.add_button)
        layout.addLayout(row)
        self.list = QListWidget()
        self.list.setItemDelegate(TodoRowDelegate(self.list))
        self.list.setSpacing(5)
        layout.addWidget(self.list)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.delete_button = QPushButton("删除选中")
        self.delete_button.setAutoDefault(False)
        self.delete_button.setEnabled(False)
        layout.addWidget(self.delete_button)
        self.setStyleSheet("QPushButton{background:#ed7d24;color:white;border:0;border-radius:10px;padding:8px;} QPushButton:disabled{background:#d4b99e;} QListWidget{border:1px solid #ead8c5;border-radius:8px;padding:6px;} QLineEdit{padding:7px;}")
        self.add_button.clicked.connect(self.add_task)
        self.input.returnPressed.connect(self.add_task)
        self.list.itemChanged.connect(self._changed)
        self.list.itemSelectionChanged.connect(lambda: self.delete_button.setEnabled(bool(self.list.selectedItems())))
        self.delete_button.clicked.connect(self.delete_selected)
        self._load()
        self._refresh()

    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or any(
                not isinstance(t, dict) or not isinstance(t.get("text"), str) or
                not isinstance(t.get("id"), str) for t in data):
                raise ValueError("invalid tasks")
            self.tasks = data
        except (OSError, ValueError):
            self.status.setText("待办文件读取失败，原文件已保留。请检查文件后重新打开程序。")
            self.add_button.setEnabled(False)
            self.input.setEnabled(False)
            self.list.setEnabled(False)

    def _save(self):
        temp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.path)
            self.status.setStyleSheet("color:#888;")
            self._count()
            return True
        except OSError:
            self.status.setStyleSheet("color:#b54032;")
            self.status.setText("保存失败，本次修改未保存，请检查本地文件权限。")
            return False

    def _count(self):
        pending = sum(not t.get("done", False) for t in self.tasks)
        self.status.setText(f"{pending} 项待办 · {len(self.tasks) - pending} 项已完成" if self.tasks else "暂无待办，添加一件小事吧。")

    def _refresh(self):
        self._loading = True
        self.list.clear()
        for task in self.tasks:
            item = QListWidgetItem(task["text"])
            item.setData(Qt.UserRole, task["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if task.get("done", False) else Qt.Unchecked)
            font = QFont(item.font())
            font.setStrikeOut(bool(task.get("done", False)))
            item.setFont(font)
            self.list.addItem(item)
            row = QWidget()
            row.setAutoFillBackground(True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            checkbox = QCheckBox(task["text"])
            checkbox.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            checkbox.setChecked(bool(task.get("done", False)))
            checkbox.setFont(font)
            checkbox.setToolTip(task["text"])
            text_column = QVBoxLayout()
            text_column.addWidget(checkbox)
            if isinstance(task.get("due"), (int, float)):
                due_label = QLabel(QDateTime.fromSecsSinceEpoch(int(task["due"])).toString("MM-dd HH:mm") + (" · 已提醒" if task.get("notified") else " · 提醒"))
                due_label.setStyleSheet("color:#888;font-size:11px;")
                text_column.addWidget(due_label)
            row_layout.addLayout(text_column, 1)
            remind = QPushButton("修改提醒" if isinstance(task.get("due"), (int, float)) else "提醒")
            remind.setAutoDefault(False)
            remind.setObjectName("remind_" + task["id"])
            remind.setCursor(Qt.PointingHandCursor)
            remind.setToolTip("选择这条事项的提醒日期和时间")
            remind.clicked.connect(lambda checked=False, task_id=task["id"]: self._set_row_due(task_id))
            row_layout.addWidget(remind)
            delete = QPushButton("删除")
            delete.setAutoDefault(False)
            delete.setObjectName("delete_" + task["id"])
            delete.setCursor(Qt.PointingHandCursor)
            delete.setStyleSheet("QPushButton{background:#fff0e5;color:#b95028;padding:6px 10px;} QPushButton:hover{background:#ffddc5;}")
            delete.clicked.connect(lambda checked=False, task_id=task["id"]: self._delete_ids({task_id}))
            row_layout.addWidget(delete)
            checkbox.toggled.connect(lambda checked, target=item: target.setCheckState(Qt.Checked if checked else Qt.Unchecked))
            hint = row.sizeHint()
            hint.setWidth(0)
            item.setSizeHint(hint)
            self.list.setItemWidget(item, row)
        self._loading = False
        if self.input.isEnabled():
            self._count()

    def add_task(self):
        text = self.input.text().strip()
        if not text or not self.input.isEnabled():
            return
        old = list(self.tasks)
        self.tasks.append({"id": str(uuid.uuid4()), "text": text, "done": False,
                           "due": None, "notified": False})
        if self._save():
            self.input.clear()
            self._refresh()
        else:
            self.tasks = old

    def _changed(self, item):
        if self._loading:
            return
        task = next(t for t in self.tasks if t["id"] == item.data(Qt.UserRole))
        old = task.get("done", False)
        task["done"] = item.checkState() == Qt.Checked
        if not self._save():
            task["done"] = old
            message = self.status.text()
            self._refresh()
            self.status.setText(message)
            return
        self._loading = True
        font = QFont(item.font())
        font.setStrikeOut(task["done"])
        item.setFont(font)
        row = self.list.itemWidget(item)
        if row:
            checkbox = row.findChild(QCheckBox)
            checkbox.blockSignals(True)
            checkbox.setChecked(task["done"])
            checkbox.setFont(font)
            checkbox.blockSignals(False)
        self._loading = False
        if task["done"] and not old:
            self.task_completed.emit(task["text"])

    def _set_row_due(self, task_id):
        task = next((task for task in self.tasks if task["id"] == task_id), None)
        if task is None:
            return
        editor = ReminderTimeDialog(task, self)
        try:
            if editor.exec_() != QDialog.Accepted:
                return
            due = editor.reminder_due
        finally:
            editor.deleteLater()
        # Due reminders may refresh the list while the modal editor is open.
        # Resolve by stable task ID rather than retaining a QListWidgetItem.
        task = next((task for task in self.tasks if task["id"] == task_id), None)
        if task is None:
            return
        old = [dict(t) for t in self.tasks]
        task.update(due=due, notified=False)
        if self._save():
            self._refresh()
        else:
            self.tasks = old

    def due_tasks(self, now):
        return [t for t in self.tasks if not t.get("done") and not t.get("notified")
                and isinstance(t.get("due"), (int, float)) and t["due"] <= now]

    def mark_reminded(self, task_id, due):
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task or task.get("done") or task.get("due") != due:
            return False
        task["notified"] = True
        if not self._save():
            task["notified"] = False
            return False
        self._refresh()
        return True

    def delete_selected(self):
        ids = {item.data(Qt.UserRole) for item in self.list.selectedItems()}
        self._delete_ids(ids)

    def _delete_ids(self, ids):
        if not ids:
            return
        old = self.tasks
        self.tasks = [t for t in self.tasks if t["id"] not in ids]
        if self._save():
            self._refresh()
        else:
            self.tasks = old
