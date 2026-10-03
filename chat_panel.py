"""奶油橙聊天面板：原生消息气泡、快捷话题和后台 LLM 请求。"""
import os

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent, QPointF
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPixmap, QFont, QKeySequence
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QLineEdit, QPushButton, QLabel, QFrame, QSizePolicy,
                             QGraphicsDropShadowEffect, QShortcut, QApplication)

from config import ASSETS_DIR


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



class CatAvatar(QWidget):
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAccessibleName("猫咪头像")
        self._cat = QPixmap(os.path.join(ASSETS_DIR, "cat", "sitting-idle", "idle_000.png"))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        circle = QPainterPath()
        circle.addEllipse(0, 0, self.width(), self.height())
        painter.fillPath(circle, QColor("#ffb45f"))
        painter.setClipPath(circle)
        if not self._cat.isNull():
            image = self._cat.scaled(self.width() - 4, self.height() - 3,
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap((self.width() - image.width()) // 2,
                               self.height() - image.height() + 1, image)


class SendButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 46)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("发送消息")
        self.setToolTip("发送（Enter）")
        self.setStyleSheet("""
            QPushButton { background:#ffa447; border:0; border-radius:23px; }
            QPushButton:hover { background:#ff9333; }
            QPushButton:pressed { background:#f48125; }
            QPushButton:disabled { background:#f6cf9f; }
            QPushButton:focus { border:2px solid #ce6c1c; }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        if not self.isEnabled():
            for x in (15, 23, 31):
                painter.drawEllipse(QPointF(x, 23), 2, 2)
        else:
            plane = QPainterPath()
            plane.moveTo(15, 14)
            plane.lineTo(35, 23)
            plane.lineTo(15, 32)
            plane.lineTo(19, 23)
            plane.closeSubpath()
            painter.drawPath(plane)


class MessageBubble(QFrame):
    def __init__(self, text, role, max_width, parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName("messageBubble")
        self.label = QLabel(text)
        self.label.setTextFormat(Qt.PlainText)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setAccessibleName({"user": "你的消息", "assistant": "小猫的回复", "notice": "提醒"}[role])
        self.label.setFont(QFont("Microsoft YaHei", 10 if role == "notice" else 11))
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        color = "#ffffff" if role == "user" else "#624c39"
        background = "#ff9d3e" if role == "user" else "#fff0dd"
        radius = 21 if role != "notice" else 10
        if role == "notice":
            color, background = "#a68b70", "#faf3ea"
        corner = "border-bottom-right-radius:8px;" if role == "user" else "border-bottom-left-radius:8px;"
        self.setStyleSheet(f"""
            QFrame#messageBubble {{ background:{background}; border:0; border-radius:{radius}px; {corner} }}
            QLabel {{ color:{color}; background:transparent; border:0; padding:0; }}
        """)
        layout = QVBoxLayout(self)
        horizontal, vertical = (13, 8) if role == "notice" else (15, 12)
        layout.setContentsMargins(horizontal, vertical, horizontal, vertical)
        layout.addWidget(self.label)
        natural_width = max((self.label.fontMetrics().horizontalAdvance(line) for line in text.splitlines()), default=0)
        self.setFixedWidth(min(max_width, max(64, natural_width + horizontal * 2 + 4)))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)


class ChatPanel(QWidget):
    WIDTH = 500
    HEIGHT = 560

    def __init__(self, llm, pet_name="小戒"):
        super().__init__()
        self.llm = llm
        self.pet_name = pet_name
        self.history = []
        self.messages = []
        self._worker = None
        self._busy = False
        self._drag_pos = None
        self._init_window()
        self._init_ui()

    def _init_window(self):
        self.setWindowTitle(f"{self.pet_name} · 聊天")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.WIDTH = min(self.WIDTH, max(320, available.width() - 20))
            self.HEIGHT = min(self.HEIGHT, max(380, available.height() - 20))
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def _init_ui(self):
        self.setFont(QFont("Microsoft YaHei", 10))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        self.card = QFrame(self)
        self.card.setObjectName("chatCard")
        self.card.setStyleSheet("QFrame#chatCard { background:#fffaf5; border:1px solid #efdfcc; border-radius:28px; }")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(117, 74, 26, 24))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self.header = QWidget()
        self.header.setFixedHeight(80)
        title = QHBoxLayout(self.header)
        title.setContentsMargins(21, 15, 16, 12)
        title.setSpacing(12)
        avatar = CatAvatar(44)
        title.addWidget(avatar)
        title_text = QVBoxLayout()
        title_text.setSpacing(2)
        self.title_label = QLabel(self.pet_name)
        self.title_label.setStyleSheet("color:#59432e; font-size:18px; font-weight:600; background:transparent;")
        self.subtitle = QLabel("在线陪你 · 听你说说今天的事")
        self.subtitle.setStyleSheet("color:#aa8e71; font-size:12px; background:transparent;")
        title_text.addWidget(self.title_label)
        title_text.addWidget(self.subtitle)
        title.addLayout(title_text, 1)
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setAccessibleName("收起聊天")
        close_btn.setToolTip("收起聊天（Esc）")
        close_btn.setStyleSheet("QPushButton{border:0;border-radius:12px;background:transparent;color:#b49c86;font-size:19px;} QPushButton:hover{background:#ffecd6;color:#d07d39;}")
        close_btn.clicked.connect(self.hide)
        title.addWidget(close_btn, 0, Qt.AlignTop)
        for widget in (self.header, avatar, self.title_label, self.subtitle):
            widget.installEventFilter(self)
        layout.addWidget(self.header)
        layout.addWidget(self._divider())

        self.browser = QScrollArea()
        self.browser.setWidgetResizable(True)
        self.browser.setFrameShape(QFrame.NoFrame)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setStyleSheet("""
            QScrollArea { background:transparent; border:0; }
            QScrollArea > QWidget > QWidget { background:transparent; }
            QScrollBar:vertical { background:transparent; width:7px; margin:8px 1px; }
            QScrollBar::handle:vertical { background:#efdbba; border-radius:3px; min-height:35px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        """)
        self.message_area = QWidget()
        self.message_area.setObjectName("messageArea")
        self.message_area.setStyleSheet("#messageArea { background:transparent; }")
        self.message_layout = QVBoxLayout(self.message_area)
        self.message_layout.setContentsMargins(20, 15, 20, 15)
        self.message_layout.setSpacing(14)
        self.message_layout.addStretch(1)
        self.browser.setWidget(self.message_area)
        # Wrapped labels can update the scroll range after the first layout pass.
        self.browser.verticalScrollBar().rangeChanged.connect(
            lambda minimum, maximum: self.browser.verticalScrollBar().setValue(maximum))
        layout.addWidget(self.browser, 1)

        self.quick_area = QWidget()
        quick_layout = QVBoxLayout(self.quick_area)
        quick_layout.setContentsMargins(20, 8, 20, 10)
        quick_layout.setSpacing(8)
        self.quick_buttons = []
        self._quick_rows = []
        for _ in range(2):
            row = QHBoxLayout()
            row.setSpacing(7)
            row.addStretch(1)
            quick_layout.addLayout(row)
            self._quick_rows.append(row)
        # Two balanced rows keep the topics readable on desktop screens.
        prompts = [f"{self.pet_name}今天吃饭了吗？", "陪我聊聊天", "我心情不太好", "讲个笑话喵"]
        for index, prompt in enumerate(prompts):
            button = QPushButton(prompt)
            button.setFixedHeight(32)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton { background:#ffe9cf; color:#ed8a3d; border:1px solid transparent; border-radius:16px; padding:0 13px; font-size:12px; }
                QPushButton:hover { background:#ffdfb7; border:1px dashed #ff9c44; }
                QPushButton:focus { border:1px dashed #ff9c44; }
                QPushButton:disabled { color:#bda58c; background:#f4e8d9; }
            """)
            button.clicked.connect(lambda checked=False, b=button: self._quick_send(b.text()))
            self.quick_buttons.append(button)
            # Match the reference's three topics on the first row when they fit.
            row_index = 0 if index < 3 and self.WIDTH >= 480 else (0 if index < 2 else 1)
            if self.WIDTH >= 480 and index == 3:
                row_index = 1
            row = self._quick_rows[row_index]
            row.insertWidget(row.count() - 1, button)
        layout.addWidget(self.quick_area)
        layout.addWidget(self._divider())

        composer = QWidget()
        input_row = QHBoxLayout(composer)
        input_row.setContentsMargins(20, 15, 20, 16)
        input_row.setSpacing(10)
        self.input = QLineEdit()
        self.input.setFixedHeight(46)
        self.input.setAccessibleName("聊天消息")
        self.input.setPlaceholderText(f"和{self.pet_name}说点什么吧…")
        self.input.setStyleSheet("""
            QLineEdit { border:1px solid #ecdac3; border-radius:23px; padding:0 16px; background:#ffffff; color:#624c39; font-size:14px; selection-background-color:#ffddb3; }
            QLineEdit:focus { border:2px solid #ffb66b; }
        """)
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input, 1)
        self._send_btn = SendButton()
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._send_btn)
        layout.addWidget(composer)
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._escape_shortcut.activated.connect(self.hide)
        self._append_message(f"你好，我是{self.pet_name}。", "assistant")

    @staticmethod
    def _divider():
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background:#f0dfc9; border:0;")
        return divider

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            return True
        if event.type() == QEvent.MouseMove and self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            return True
        if event.type() == QEvent.MouseButtonRelease:
            self._drag_pos = None
        return super().eventFilter(watched, event)

    def set_pet_name(self, name):
        self.pet_name = name
        self.setWindowTitle(f"{name} · 聊天")
        self.title_label.setText(name)
        self.input.setPlaceholderText(f"和{name}说点什么吧…")
        self.quick_buttons[0].setText(f"{name}今天吃饭了吗？")

    def _append_message(self, text, role):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        max_width = self.WIDTH - (160 if role == "assistant" else 125)
        bubble = MessageBubble(text, role, max_width)
        if role == "user":
            row_layout.addStretch(1)
            row_layout.addWidget(bubble)
        elif role == "assistant":
            row_layout.addWidget(CatAvatar(30), 0, Qt.AlignBottom)
            row_layout.addWidget(bubble)
            row_layout.addStretch(1)
        else:
            row_layout.addStretch(1)
            row_layout.addWidget(bubble)
            row_layout.addStretch(1)
        self.message_layout.insertWidget(self.message_layout.count() - 1, row)
        self.messages.append((role, text))
        QTimer.singleShot(0, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self):
        self.message_layout.activate()
        self.browser.verticalScrollBar().setValue(self.browser.verticalScrollBar().maximum())

    def push_system_message(self, text, level="info"):
        self._append_message(text, "notice")

    def _quick_send(self, text):
        if self._busy:
            return
        draft = self.input.text()
        self.input.setText(text)
        self._send()
        self.input.setText(draft)
        self.input.setFocus()

    def _set_busy(self, busy):
        self._busy = busy
        self._send_btn.setEnabled(not busy)
        self._send_btn.setAccessibleName("正在思考" if busy else "发送消息")
        self.subtitle.setText("正在认真想，稍等一下…" if busy else "在线陪你 · 听你说说今天的事")
        for button in self.quick_buttons:
            button.setEnabled(not busy)

    def _send(self):
        text = self.input.text().strip()
        if not text or self._busy or (self._worker is not None and self._worker.isRunning()):
            return
        self.input.clear()
        self._append_message(text, "user")
        self._set_busy(True)
        self._pending_user_text = text
        self._worker = _LLMWorker(self.llm, text, self.history[-4:])
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
        self._append_message(reply, "assistant")
        self._set_busy(False)

    @staticmethod
    def _escape(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
