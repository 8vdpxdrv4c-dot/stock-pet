"""Quiet-mode reminder queue, due tasks and sedentary reminders."""
import ctypes
import os
import time
from ctypes import wintypes
from collections import OrderedDict
from PyQt5.QtCore import QObject, QTimer, Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


def foreground_fullscreen():
    if os.name != "nt":
        return False
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    hwnd = user.GetForegroundWindow()
    if not hwnd:
        return False
    name = ctypes.create_unicode_buffer(256)
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetClassNameW(hwnd, name, 256)
    if name.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
        return False
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return False
    class Info(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
    user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user.MonitorFromWindow.restype = wintypes.HANDLE
    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    rect, info = wintypes.RECT(), Info()
    info.size = ctypes.sizeof(info)
    if not user.GetWindowRect(hwnd, ctypes.byref(rect)) or not user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
        return False
    m = info.monitor
    return rect.left <= m.left and rect.top <= m.top and rect.right >= m.right and rect.bottom >= m.bottom


class RestDialog(QDialog):
    def __init__(self, manager):
        super().__init__(manager.app.pet)
        self.manager = manager
        self.setWindowTitle("活动一下")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        label = QLabel("主人，站起来走走、活动一下肩颈吧~喵")
        label.setWordWrap(True)
        layout.addWidget(label)
        row = QHBoxLayout()
        for title, minutes in (("稍后提醒（5分钟）", 5), ("已活动", None)):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, delay=minutes: self.finish(delay))
            row.addWidget(button)
        layout.addLayout(row)
        self.setStyleSheet("QPushButton{background:#ed7d24;color:white;border:0;border-radius:10px;padding:10px;} QLabel{padding:10px;}")

    def finish(self, minutes):
        self.manager.rest_due = time.time() + (minutes or self.manager.rest_interval) * 60
        self.hide()

    def reject(self):
        self.finish(5)

    def closeEvent(self, event):
        self.finish(5)
        event.accept()


class ReminderManager(QObject):
    def __init__(self, app, cfg):
        super().__init__(app.pet)
        self.app = app
        self.focus = False
        self.quiet = False
        self.pending = OrderedDict()
        self.next_display = 0
        self.rest_dialog = RestDialog(self)
        self.configure(cfg)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def configure(self, cfg):
        settings = cfg.get("wellness", {})
        self.rest_enabled = settings.get("enabled", True)
        self.rest_interval = max(1, min(180, int(settings.get("interval_minutes", 60))))
        self.auto_quiet = cfg.get("quiet_mode", {}).get("fullscreen", True)
        self.rest_due = time.time() + self.rest_interval * 60
        self.pending.pop("rest", None)
        if not self.rest_enabled:
            self.rest_dialog.hide()

    def is_quiet(self):
        return self.focus or (self.auto_quiet and foreground_fullscreen())

    def set_focus(self, enabled):
        self.focus = enabled
        self.tick()

    def enqueue(self, key, callback):
        self.pending[key] = callback

    def tick(self):
        now = time.time()
        quiet = self.is_quiet()
        if quiet and not self.quiet:
            self.app.speech.bubble.hide()
            if self.rest_dialog.isVisible():
                self.rest_dialog.hide()
                self.enqueue("rest", self.show_rest)
        self.quiet = quiet
        for task in self.app.todo.due_tasks(now):
            task_id, due, text = task["id"], task["due"], task["text"]
            self.enqueue(("todo", task_id, due),
                         lambda i=task_id, d=due, t=text: self.show_task(i, d, t))
        if self.rest_enabled and now >= self.rest_due and not self.rest_dialog.isVisible():
            self.enqueue("rest", self.show_rest)
        if quiet or getattr(self.app, "_busy_walk", False) or now < self.next_display:
            return
        if self.pending:
            _, callback = self.pending.popitem(last=False)
            callback()
            self.next_display = now + 9

    def show_task(self, task_id, due, text):
        if self.app.todo.mark_reminded(task_id, due):
            self.app.speech.say_once("主人，待办到时间啦：" + text)

    def show_rest(self):
        if self.rest_enabled:
            self.app.speech.say_once("主人，站起来走走、活动一下肩颈吧~喵")
            self.rest_dialog.show()

    def stop(self):
        self.timer.stop()
        self.pending.clear()
        self.rest_dialog.hide()
