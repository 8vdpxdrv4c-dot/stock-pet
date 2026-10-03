"""Mindback 文字记录：后台发送，登录会话存 Windows 凭据管理器。"""
import json
import time
import uuid
import urllib.request
import urllib.error
from urllib.parse import urlencode

import keyring
from PyQt5.QtCore import QThread, pyqtSignal, QSettings, Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QLabel, QPushButton

URL = "https://www.mindback.chat/api/mindback/v1/profile/chat/send_mindback_message"
WEBID = "7481d563-5895-4aa3-bd83-2950290be06a"


def send_record(text, sequence):
    sid = keyring.get_password("StockPet", "mindback_session")
    if not sid:
        raise ValueError("缺少登录会话，请提供登录后请求头中 xy-common-params 的 sid。")
    common = dict(appAlias="campusx", app_id="F98AF402", auto_trans=0, build=1,
                  channel="GooglePlay", deviceId=WEBID, device_model="Web", dlang="zh",
                  fid="", gid="", holder_ctry="CN", identifier_flag=0, is_mac=0,
                  launch_id="019176a6-be55-47fe-ac03-a5f2dcb35a63", mlanguage="zh_cn",
                  overseas_channel=0, platform="WEB", project_id="F98AF4",
                  t=int(time.time()), tz="Asia/Shanghai", uis="light", version="1.0.1", sid=sid)
    payload = dict(messageId=str(uuid.uuid4()), chatId=2650536, clientSeq=sequence,
                   sendTime=int(time.time() * 1000),
                   message=json.dumps({"type": "text", "text": text}, ensure_ascii=False))
    request = urllib.request.Request(URL, method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "Origin": "https://www.mindback.chat", "Referer": "https://www.mindback.chat/chat",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
                 "webid": WEBID, "xy-common-params": urlencode(common)})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ValueError("登录会话失效，请重新登录网站，提供最新 xy-common-params 中的 sid。") from None
        raise ValueError(f"接口返回 HTTP {exc.code}，记录未确认发送，请稍后重试。") from None
    if result.get("success") is not True or result.get("data", {}).get("acceptCode") != "ACK":
        message = str(result.get("msg", "未收到发送确认")).replace(sid, "[已隐藏]")
        raise ValueError(f"发送未成功：{message}。如提示登录失效，请更新登录会话。")
    return result["data"].get("lastAckClientSeq", sequence)


class RecordWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, text, sequence, parent=None):
        super().__init__(parent)
        self.text, self.sequence = text, sequence
        self.ack = sequence

    def run(self):
        try:
            self.ack = send_record(self.text, self.sequence)
            self.completed.emit(True, "记录已发送到 Mindback。")
        except ValueError as exc:
            self.completed.emit(False, str(exc))
        except Exception:
            self.completed.emit(False, "连接失败或超时，尚未确认发送，请检查网络后重试。")


class RecordDialog(QDialog):
    sent = pyqtSignal(str)

    def __init__(self, pet):
        super().__init__(pet)
        self.setWindowTitle("记录")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.resize(420, 300)
        self.worker = None
        self._send_succeeded = False
        self.store = QSettings("StockPet", "Mindback")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("写下想记录的内容，发送到 Mindback"))
        self.input = QTextEdit()
        self.input.setPlaceholderText("今天有什么想记下来的？")
        layout.addWidget(self.input)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.send_button = QPushButton("发送记录")
        self.send_button.setStyleSheet("QPushButton{background:#ed7d24;color:white;border:0;border-radius:12px;padding:10px;} QPushButton:disabled{background:#d4b99e;}")
        self.send_button.clicked.connect(self.send)
        layout.addWidget(self.send_button)

    def send(self):
        text = self.input.toPlainText().strip()
        if not text or (self.worker and self.worker.isRunning()):
            self.status.setText("请输入记录内容。" if not text else "正在发送，请稍候。")
            return
        sequence = max(53, int(self.store.value("clientSeq", 53))) + 1
        self.store.setValue("clientSeq", sequence)
        self.store.sync()
        self.send_button.setEnabled(False)
        self._send_succeeded = False
        self.input.setReadOnly(True)
        self.status.setText("正在发送…")
        self.worker = RecordWorker(text, sequence, self)
        self.worker.completed.connect(self._completed)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _completed(self, ok, message):
        self._send_succeeded = ok
        self.status.setText(message)
        self.status.setStyleSheet("color:#38804b;" if ok else "color:#b54032;")
        if ok:
            self.input.clear()
            self.store.setValue("clientSeq", max(int(self.store.value("clientSeq", 53)), int(self.worker.ack)))

    def _finished(self):
        self.send_button.setEnabled(True)
        self.input.setReadOnly(False)
        if self._send_succeeded:
            self.accept()
            self.sent.emit("记录发送成功，已帮你记下啦~喵")

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.status.setText("正在发送，请等待结果后关闭。")
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)
