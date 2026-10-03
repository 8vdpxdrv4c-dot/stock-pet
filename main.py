"""桌面宠物 - 入口。"""
import logging
import sys
import time

from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal, QPropertyAnimation
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction)

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

import win_recycle
from config import load_config
from llm_client import LLMClient
from question_memory import QuestionMemory
from pet_widget import PetWidget
from chat_panel import ChatPanel
from pet_actions import PetActions
from speech_bubble import SpeechReminder
from mindback_record import RecordDialog
from todo_dialog import TodoDialog
from reminder_manager import ReminderManager
from settings_dialog import SettingsDialog


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("stock_pet")


def _make_tray_icon():
    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(255, 138, 165)))
    p.setPen(QPen(QColor(200, 80, 110), 2))
    p.drawEllipse(6, 6, 52, 52)
    p.setPen(QPen(QColor(255, 255, 255), 2))
    p.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, "戒")
    p.end()
    return QIcon(pix)


class _EmptyBinWorker(QThread):
    """清空回收站放后台线程：SHEmptyRecycleBin 是阻塞调用，不能卡住界面。"""
    done = pyqtSignal(bool, str)

    def run(self):
        ok, msg = win_recycle.empty_recycle_bin()
        self.done.emit(ok, msg)


class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        self.cfg = load_config()
        self.pet_name = self.cfg.get("pet_name", "小戒")
        self._busy_walk = False
        self._home_pos = None
        self._home_animation = None
        self._recycle_result_text = None
        self._empty_worker = None
        self.llm = self._build_llm(self.cfg)
        self.pet = PetWidget(self.pet_name, self.cfg.get("pet_scale_percent", 100))
        self.pet.show()
        self.chat = ChatPanel(self.llm, self.pet_name)
        self.actions = PetActions(self.pet)
        self.speech = SpeechReminder(self.pet, self.cfg)
        self.record = RecordDialog(self.pet)
        self.record.sent.connect(self.speech.say_once)
        self.todo = TodoDialog(self.pet)
        self.reminders = ReminderManager(self, self.cfg)
        self.speech.timer.timeout.disconnect(self.speech.say_once)
        self.speech.timer.timeout.connect(lambda: self.reminders.enqueue("water", self.speech.say_once))
        self.todo.task_completed.connect(lambda text: self.reminders.enqueue("completed", lambda: self._celebrate_task(text)))
        self._wire_signals()
        self._setup_tray()
        QTimer.singleShot(500, self._after_start)

    @staticmethod
    def _build_llm(cfg):
        return LLMClient(
            api_key=cfg.get("deepseek_api_key", ""),
            base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com"),
            model=cfg.get("deepseek_model", "deepseek-chat"),
            system_prompt=cfg.get("system_prompt", ""),
            question_memory=QuestionMemory(),
        )

    def _after_start(self):
        self.chat.push_system_message(f"{self.pet_name}已上线。", "info")
        if not self.cfg.get("deepseek_api_key"):
            QTimer.singleShot(300, self._open_settings)
        elif "--settings" in sys.argv:
            self._open_settings()
        elif "--chat" in sys.argv:
            self._on_pet_action("chat")
        elif "--todo" in sys.argv:
            self._on_pet_action("todo")

    def _wire_signals(self):
        self.pet.clicked.connect(self.actions.toggle)
        self.pet.clicked.connect(self.speech.bubble.hide)
        self.actions.action_requested.connect(self._on_pet_action)
        self.pet.quit_requested.connect(self._quit)
        self.pet.open_settings_requested.connect(self._open_settings)
        self.pet.empty_recycle_requested.connect(self._on_empty_recycle)
        self.pet.focus_toggled.connect(self.reminders.set_focus)

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, parent=self.pet)
        dlg.saved.connect(self._on_settings_saved)
        dlg.speech_preview.connect(self.speech.say_once)
        dlg.exec_()

    def _on_settings_saved(self, new_cfg):
        self.cfg = new_cfg
        self.pet_name = new_cfg.get("pet_name", "小戒")
        self.llm = self._build_llm(new_cfg)
        self.chat.llm = self.llm
        self.chat.set_pet_name(self.pet_name)
        self.pet.pet_name = self.pet_name
        self.pet.set_scale_percent(new_cfg.get("pet_scale_percent", 100))
        self.speech.configure(new_cfg)
        self.reminders.configure(new_cfg)
        if self.chat.isVisible():
            self._place_panel_above_pet()
        self.pet.update()
        self.chat.push_system_message("设置已保存 ✅", "happy")

    def _toggle_chat(self):
        self.actions.hide()
        if self.chat.isVisible():
            self.chat.hide()
        else:
            self._place_panel_above_pet()
            self.chat.show()
            self.chat.activateWindow()

    def _on_pet_action(self, action):
        if action == "chat":
            self._place_panel_above_pet()
            self.chat.show()
            self.chat.raise_()
            self.chat.activateWindow()
            self.chat.input.setFocus()
        elif action == "eat":
            self.pet.start_eating()
        elif action == "sleep":
            self.pet.start_sleeping()
        elif action == "transform":
            self.pet.start_transform()
        elif action == "record":
            self.record.show()
            self.record.raise_()
            self.record.activateWindow()
            self.record.input.setFocus()
        elif action == "todo":
            self.todo.show()
            self.todo.raise_()
            self.todo.activateWindow()
            self.todo.input.setFocus()

    def _place_panel_above_pet(self):
        pr = self.pet.frameGeometry()
        x = pr.center().x() - self.chat.WIDTH // 2
        y = pr.top() - self.chat.HEIGHT - 5
        screen = self.qapp.primaryScreen().availableGeometry()
        x = max(screen.left(), min(x, screen.right() - self.chat.WIDTH))
        y = max(screen.top(), y)
        self.chat.move(x, y)

    def _celebrate_task(self, text):
        self.speech.say_once("主人，完成了一件事，真棒~喵！")
        state = self.pet.animation_state()
        home = QPoint(self.pet.pos())
        self.pet.start_idle()
        self.pet.set_mood("happy")
        self._celebration = QPropertyAnimation(self.pet, b"pos", self.pet)
        self._celebration.setDuration(600)
        for fraction, offset in ((0, 0), (.25, -8), (.5, 0), (.75, -5), (1, 0)):
            self._celebration.setKeyValueAt(fraction, home + QPoint(0, offset))
        self._celebration.finished.connect(lambda: self.pet.restore_animation_state(state))
        self._celebration.start()

    # ---------- 清空回收站 ----------
    def _on_empty_recycle(self):
        if self._busy_walk:
            self.chat.push_system_message("我还在路上呢，等我站稳了再点。", "info")
            return
        self._home_pos = QPoint(self.pet.pos())
        self._home_animation = self.pet.animation_state()
        self._recycle_result_text = None
        self._busy_walk = True
        icon = win_recycle.find_recycle_bin_icon()
        if not icon:
            self.chat.push_system_message("桌面上没找到回收站图标（可能被隐藏了），我随便挑个地方动手。", "warn")
        self.chat.push_system_message("去清空回收站，等我一下…", "info")
        self.pet.set_mood("happy")
        self.pet.start_idle()
        self.pet.walk_to(self._walk_target_for(icon), on_arrive=self._start_empty_recycle, recycle=True)

    def _walk_target_for(self, icon):
        """Align the visible eating cat's torso with the actual recycle icon center."""
        w, h = self.pet.width(), self.pet.height()
        left, top, right, bottom = icon if icon else (24, 24, 96, 96)
        center = self.pet.eating_body_center()
        x = round((left + right) / 2 - center.x())
        y = round((top + bottom) / 2 - center.y())
        screen = self.qapp.primaryScreen()
        hit = self.qapp.screenAt(QPoint((left + right) // 2, (top + bottom) // 2))
        if hit is not None:
            screen = hit
        geo = screen.availableGeometry()
        if not icon:
            x = max(geo.left(), min(x, geo.right() - w))
            y = max(geo.top(), min(y, geo.bottom() - h))
        return QPoint(x, y)

    def _start_empty_recycle(self):
        self.pet.start_eating()
        self._recycle_eating_started = time.monotonic()
        self._empty_worker = _EmptyBinWorker()
        self._empty_worker.done.connect(self._on_empty_done)
        self._empty_worker.start()

    def _on_empty_done(self, ok, msg):
        self.pet.set_mood("happy" if ok else "warn", True)
        self._recycle_result_text = "主人，帮你清理干净了" if ok else msg
        # Let the eating loop finish once, even when Windows empties the bin instantly.
        remaining = max(0, 3200 - int((time.monotonic() - self._recycle_eating_started) * 1000))
        QTimer.singleShot(remaining, self._walk_home)

    def _walk_home(self):
        home = self._home_pos
        self.pet.start_idle()
        if home is None:
            self._finish_recycle_trip()
            return
        self.pet.walk_to(home, on_arrive=self._finish_recycle_trip, recycle=True)

    def _finish_recycle_trip(self):
        if self._home_animation is not None:
            self.pet.restore_animation_state(self._home_animation)
        self._home_animation = None
        self._home_pos = None
        self._busy_walk = False
        if self._recycle_result_text:
            self.speech.say_once(self._recycle_result_text)
            self._recycle_result_text = None

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_make_tray_icon(), self.qapp)
        self.tray.setToolTip(f"{self.pet_name} · 桌面宠物")
        menu = QMenu()
        for text, slot in [("打开聊天", self._toggle_chat), ("设置", self._open_settings)]:
            a = QAction(text, None)
            a.triggered.connect(slot)
            menu.addAction(a)
        menu.addSeparator()
        a = QAction("退出", None)
        a.triggered.connect(self._quit)
        menu.addAction(a)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self._toggle_chat() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _quit(self):
        if self.record.worker and self.record.worker.isRunning():
            self.record.show()
            self.record.status.setText("记录正在发送，请等待结果后退出。")
            return
        self.speech.stop()
        self.pet._idle_interaction.stop()
        self.reminders.stop()
        self.tray.hide()
        self.qapp.quit()

    def run(self):
        return self.qapp.exec_()


def main():
    app = App()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
