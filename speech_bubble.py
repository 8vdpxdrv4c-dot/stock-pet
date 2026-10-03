"""轻量的桌宠文字气泡和定时提醒，不调用网络或语音服务。"""
from PyQt5.QtCore import Qt, QTimer, QEvent, QRect, QRectF, QObject, QPointF
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QFontMetrics, QLinearGradient
from PyQt5.QtWidgets import QWidget, QLabel, QApplication

from config import DEFAULT_SPEECH_TEXT


class SpeechBubble(QWidget):
    def __init__(self, pet):
        super().__init__(pet, Qt.Tool | Qt.FramelessWindowHint |
                         Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus |
                         Qt.WindowTransparentForInput)
        self.pet = pet
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.PlainText)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Microsoft YaHei", 12))
        self.label.setStyleSheet("color:#684633;background:transparent;")
        self._tail_x = 140
        self._tail_up = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        pet.installEventFilter(self)

    def speak(self, text, duration_ms=8000):
        text = str(text).strip()
        if not text:
            return
        self.label.setText(text)
        bounds = (QApplication.screenAt(self.pet.frameGeometry().center()) or
                  QApplication.primaryScreen()).availableGeometry()
        width = min(304, bounds.width() - 24)
        metrics = QFontMetrics(self.label.font())
        text_bounds = metrics.boundingRect(QRect(0, 0, width - 64, 1000),
                                           Qt.TextWordWrap, text)
        self.setFixedSize(width, max(112, text_bounds.height() + 80))
        self.place_near_pet()
        self.show()
        self.raise_()
        self._hide_timer.start(duration_ms)

    def place_near_pet(self):
        rect = self.pet.frameGeometry()
        screen = QApplication.screenAt(rect.center()) or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        x = rect.center().x() - self.width() + 48
        y = rect.top() - self.height() - 6
        self._tail_up = y < bounds.top()
        if self._tail_up:
            y = rect.bottom() + 6
        x = max(bounds.left(), min(x, bounds.right() - self.width() + 1))
        y = max(bounds.top(), min(y, bounds.bottom() - self.height() + 1))
        self._tail_x = max(48, min(rect.center().x() - x, self.width() - 48))
        self.label.setGeometry(32, 42 if self._tail_up else 26,
                               self.width() - 64, self.height() - 68)
        self.move(x, y)
        self.update()

    def eventFilter(self, watched, event):
        if watched is self.pet:
            if event.type() in (QEvent.Move, QEvent.Resize) and self.isVisible():
                self.place_near_pet()
            elif event.type() in (QEvent.Hide, QEvent.Close):
                self.hide()
        return super().eventFilter(watched, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # One continuous outline keeps the tail junction free of an internal border.
        left, right = 14, self.width() - 14
        top = 30 if self._tail_up else 14
        bottom = self.height() - (18 if self._tail_up else 34)
        radius, tx = 20, self._tail_x
        path = QPainterPath(QPointF(left + radius, top))
        if self._tail_up:
            path.lineTo(tx - 7, top)
            path.lineTo(tx, top - 10)
            path.lineTo(tx + 7, top)
        path.lineTo(right - radius, top)
        path.quadTo(right, top, right, top + radius)
        path.lineTo(right, bottom - radius)
        path.quadTo(right, bottom, right - radius, bottom)
        if not self._tail_up:
            path.lineTo(tx + 7, bottom)
            path.lineTo(tx, bottom + 10)
            path.lineTo(tx - 7, bottom)
        path.lineTo(left + radius, bottom)
        path.quadTo(left, bottom, left, bottom - radius)
        path.lineTo(left, top + radius)
        path.quadTo(left, top, left + radius, top)
        path.closeSubpath()
        painter.save()
        painter.translate(0, 4)
        painter.setBrush(QColor(80, 44, 22, 14))
        for spread in range(12, 0, -2):
            painter.setPen(QPen(QColor(80, 44, 22, 5), spread,
                                Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)
        painter.restore()
        gradient = QLinearGradient(0, top, 0, bottom)
        gradient.setColorAt(0, QColor("#fffdf7"))
        gradient.setColorAt(1, QColor("#fff0db"))
        painter.setPen(QPen(QColor("#e9a66c"), 1.5,
                            Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(gradient)
        painter.drawPath(path)
        painter.end()


class SpeechReminder(QObject):
    def __init__(self, pet, cfg):
        super().__init__(pet)
        self.bubble = SpeechBubble(pet)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.say_once)
        self.configure(cfg)

    def configure(self, cfg):
        settings = cfg.get("speech_reminder", {})
        self.text = settings.get("text", DEFAULT_SPEECH_TEXT).strip() or DEFAULT_SPEECH_TEXT
        self.timer.stop()
        minutes = max(1, min(180, int(settings.get("interval_minutes", 5))))
        if settings.get("enabled", True):
            self.timer.start(minutes * 60 * 1000)
        else:
            self.bubble.hide()

    def say_once(self, text=None):
        self.bubble.speak(self.text if text is None else text)

    def stop(self):
        self.timer.stop()
        self.bubble._hide_timer.stop()
        self.bubble.hide()
