"""聊天面板：独立圆角窗口，贴在宠物上方。LLM 调用放后台线程。"""
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
                             QLineEdit, QPushButton, QLabel, QFrame)

from llm_client import LLMClient


class _LLMWorker(QThread):
    finished_ok = pyqtSignal(str)
    finished_err = pyqtSignal(str)

    def __init__(self, client, message, history):
        super().__init__()
        self.client = client
        self.message = message
        self.history = history

    def run(self):
        try:
            reply = self.client.chat(self.message, self.history)
            self.finished_ok.emit(reply)
        except Exception as e:
            self.finished_err.emit(str(e))


class ChatPanel(QWidget):
    WIDTH = 320
    HEIGHT = 420

    def __init__(self, llm, pet_name="小戒"):
        super().__init__()
        self.llm = llm
        self.pet_name = pet_name
        self.history = []
        self._worker = None
        self._drag_pos = None
        self._init_ui()
        self._init_window()

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = QFrame(self)
        card.setStyleSheet("QFrame{background-color:rgba(255,255,255,240);border-radius:14px;border:1px solid #ffd6e0;}")
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)
        title = QHBoxLayout()
        title_label = QLabel(f"🌸 {self.pet_name} · 纪律监督")
        title_label.setStyleSheet("color:#d65a7a;font-weight:bold;font-size:13px;")
        title.addWidget(title_label)
        title.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("QPushButton{border:none;color:#999;font-size:16px;}QPushButton:hover{color:#d65a7a;}")
        close_btn.clicked.connect(self.hide)
        title.addWidget(close_btn)
        layout.addLayout(title)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet("QTextBrowser{border:none;background:transparent;font-size:13px;}")
        self.browser.append(f"<p style='color:#888'>你好，我是{self.pet_name}。我会盯着你的交易纪律。<br><i>试试：「我想买了」「今天大涨我要追」</i></p>")
        layout.addWidget(self.browser, 1)
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("说点什么…（回车发送）")
        self.input.setStyleSheet("QLineEdit{border:1px solid #ffd6e0;border-radius:16px;padding:6px 12px;background:#fff;}")
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input, 1)
        send_btn = QPushButton("发送")
        send_btn.setStyleSheet("QPushButton{background:#ff8aa5;color:white;border:none;border-radius:14px;padding:6px 14px;}QPushButton:hover{background:#ff6b8a;}QPushButton:disabled{background:#ccc;}")
        send_btn.clicked.connect(self._send)
        self._send_btn = send_btn
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def push_system_message(self, text, level="info"):
        color = {"info": "#888", "warn": "#e6a23c", "panic": "#e74c3c", "happy": "#52c41a"}.get(level, "#888")
        self.browser.append(f"<p style='color:{color}'>🔔 {text}</p>")
        self.browser.verticalScrollBar().setValue(self.browser.verticalScrollBar().maximum())

    def _send(self):
        text = self.input.text().strip()
        if not text or (self._worker is not None and self._worker.isRunning()):
            return
        self.input.clear()
        self.browser.append(f"<p style='color:#333;text-align:right'><b>你：</b>{self._escape(text)}</p>")
        self._send_btn.setEnabled(False)
        self._send_btn.setText("思考…")
        self._pending_user_text = text
        self._worker = _LLMWorker(self.llm, text, self.history[-10:])
        self._worker.finished_ok.connect(self._on_reply_ok)
        self._worker.finished_err.connect(self._on_reply_err)
        self._worker.start()

    def _on_reply_ok(self, reply):
        self.history.append({"role": "user", "content": self._pending_user_text})
        self.history.append({"role": "assistant", "content": reply})
        self._render_reply(reply)

    def _on_reply_err(self, err):
        self._render_reply(f"（脑子卡住了：{err}）")

    def _render_reply(self, reply):
        self.browser.append(f"<p style='color:#d65a7a'><b>{self.pet_name}：</b>{self._escape(reply)}</p>")
        self.browser.verticalScrollBar().setValue(self.browser.verticalScrollBar().maximum())
        self._send_btn.setEnabled(True)
        self._send_btn.setText("发送")

    @staticmethod
    def _escape(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
