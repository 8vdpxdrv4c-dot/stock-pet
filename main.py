"""股票交易纪律桌面宠物 - 入口。"""
import logging
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction)

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from config import load_config
from llm_client import LLMClient
from pet_widget import PetWidget
from chat_panel import ChatPanel
from discipline_engine import DisciplineEngine
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


class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        self.cfg = load_config()
        self.pet_name = self.cfg.get("pet_name", "小戒")
        self.llm = self._build_llm(self.cfg)
        self.pet = PetWidget(self.pet_name)
        self.pet.show()
        self.chat = ChatPanel(self.llm, self.pet_name)
        self.engine = DisciplineEngine(self.cfg)
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
        )

    def _after_start(self):
        self.chat.push_system_message(f"{self.pet_name}已上线。我会在大盘异动和关键时点提醒你守纪律。", "info")
        if not self.cfg.get("deepseek_api_key"):
            QTimer.singleShot(300, self._open_settings)

    def _wire_signals(self):
        self.pet.clicked.connect(self._toggle_chat)
        self.pet.quit_requested.connect(self._quit)
        self.pet.pause_toggled.connect(self.engine.set_paused)
        self.pet.open_settings_requested.connect(self._open_settings)
        self.engine.notify.connect(self._on_notify)
        self.engine.mood_change.connect(self.pet.set_mood)

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, parent=self.pet)
        dlg.saved.connect(self._on_settings_saved)
        dlg.exec_()

    def _on_settings_saved(self, new_cfg):
        self.cfg = new_cfg
        self.pet_name = new_cfg.get("pet_name", "小戒")
        self.llm = self._build_llm(new_cfg)
        self.chat.llm = self.llm
        self.chat.pet_name = self.pet_name
        self.pet.pet_name = self.pet_name
        self.pet.update()
        try:
            self.engine._timer.stop()
        except Exception:
            pass
        self.engine = DisciplineEngine(new_cfg)
        self.engine.notify.connect(self._on_notify)
        self.engine.mood_change.connect(self.pet.set_mood)
        self.chat.push_system_message("设置已保存 ✅", "happy")

    def _toggle_chat(self):
        if self.chat.isVisible():
            self.chat.hide()
        else:
            self._place_panel_above_pet()
            self.chat.show()
            self.chat.activateWindow()

    def _place_panel_above_pet(self):
        pr = self.pet.frameGeometry()
        x = pr.center().x() - self.chat.WIDTH // 2
        y = pr.top() - self.chat.HEIGHT - 5
        screen = self.qapp.primaryScreen().availableGeometry()
        x = max(screen.left(), min(x, screen.right() - self.chat.WIDTH))
        y = max(screen.top(), y)
        self.chat.move(x, y)

    def _on_notify(self, text, level):
        log.info("[%s] %s", level, text)
        self.chat.push_system_message(text, level)
        if level in ("warn", "panic"):
            if not self.chat.isVisible():
                self._place_panel_above_pet()
                self.chat.show()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_make_tray_icon(), self.qapp)
        self.tray.setToolTip(f"{self.pet_name} · 交易纪律助手")
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
        self.tray.hide()
        self.qapp.quit()

    def run(self):
        return self.qapp.exec_()


def main():
    app = App()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
