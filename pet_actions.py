"""Icon actions arranged along an arc around the desktop pet."""
import math

from PyQt5.QtCore import Qt, QEvent, QRect, QRectF, QSize, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QRegion
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication

from action_icons import action_icon


class ActionButton(QPushButton):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_Hover)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        # Leave room for fractional alpha pixels inside the native window mask.
        circle = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        fill = QLinearGradient(circle.topLeft(), circle.bottomLeft())
        fill.setColorAt(0, QColor("#ffa64f"))
        fill.setColorAt(1, QColor("#ed7d24"))
        border, width = QColor("#ffcd9a"), 1.0
        if self.isDown():
            fill.setColorAt(0, QColor("#dc6e1d"))
            fill.setColorAt(1, QColor("#dc6e1d"))
            border, width = QColor("#ffd4ad"), 2.0
        elif self.underMouse():
            fill.setColorAt(0, QColor("#ffad58"))
            fill.setColorAt(1, QColor("#ffad58"))
            border, width = QColor("#fff0dc"), 2.0
        if self.hasFocus():
            border, width = QColor("#fff5e6"), 2.0
        painter.setPen(QPen(border, width))
        painter.setBrush(fill)
        painter.drawEllipse(circle)
        icon_rect = QRect(0, 0, self.iconSize().width(), self.iconSize().height())
        icon_rect.moveCenter(self.rect().center())
        self.icon().paint(painter, icon_rect, Qt.AlignCenter,
                          QIcon.Normal if self.isEnabled() else QIcon.Disabled)
        painter.end()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()


class PetActions(QWidget):
    action_requested = pyqtSignal(str)
    ACTIONS = (("eat", "吃饭"), ("sleep", "睡觉"), ("chat", "对话"),
               ("record", "记录"), ("todo", "待办"), ("transform", "变身"))

    def __init__(self, pet):
        super().__init__(pet, Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pet = pet
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.buttons = {}
        for key, text in self.ACTIONS:
            button = ActionButton(self)
            button.setIcon(action_icon(key))
            button.setToolTip(text)
            button.setAccessibleName(text)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, action=key: self._choose(action))
            self.buttons[key] = button
        self._style_buttons()
        pet.installEventFilter(self)

    def _style_buttons(self):
        self._button_size = max(36, min(52, 2 * round(self.pet.height() * .09)))
        for button in self.buttons.values():
            button.setFixedSize(self._button_size, self._button_size)
            button.setIconSize(QSize(round(self._button_size * .61), round(self._button_size * .61)))

    def _choose(self, action):
        self.hide()
        self.action_requested.emit(action)

    def _arrange(self, bounds):
        rect = self.pet.frameGeometry()
        center = rect.center()
        size = self._button_size
        half = size // 2
        # Grabbed pixels use the screen's device ratio; layout uses logical pixels.
        snapshot = self.pet.grab().scaled(rect.size(), Qt.IgnoreAspectRatio, Qt.FastTransformation)
        shape = QRegion(snapshot.mask()).translated(rect.topLeft())
        best, best_score = None, float("inf")
        orientations = (90, 105, 75, 120, 60, 135, 45, 150, 30, 180, 0, 225, 270, 315)
        for extra in (0, 12, 24, 36, 60, 96, 144):
            rx = rect.width() / 2 + half + 10 + extra
            ry = rect.height() / 2 + half + 10 + extra
            for span in (180, 150, 120, 210, 90, 60):
                for orientation in orientations:
                    positions = []
                    for i in range(len(self.ACTIONS)):
                        angle = math.radians(orientation + span / 2 - i * span / 5)
                        positions.append(QRect(round(center.x() + rx * math.cos(angle)) - half,
                                               round(center.y() - ry * math.sin(angle)) - half, size, size))
                    if (all(bounds.contains(box) for box in positions)
                            and all(QRegion(box.adjusted(-3, -3, 3, 3), QRegion.Ellipse).intersected(shape).isEmpty()
                                    for box in positions)
                            and all(math.hypot(a.center().x() - b.center().x(), a.center().y() - b.center().y()) >= size + 4
                                    for i, a in enumerate(positions) for b in positions[i + 1:])):
                        return positions
                    # Fallback for unusually small screens: retain all controls
                    # inside the screen and choose the least obstructed arc.
                    clamped = [QRect(max(bounds.left(), min(box.x(), bounds.right() - size + 1)),
                                     max(bounds.top(), min(box.y(), bounds.bottom() - size + 1)), size, size)
                               for box in positions]
                    score = sum(not QRegion(box, QRegion.Ellipse).intersected(shape).isEmpty() for box in clamped) * 1000
                    score += sum(a.intersects(b) for i, a in enumerate(clamped) for b in clamped[i + 1:]) * 1000
                    score += sum(abs(a.x() - b.x()) + abs(a.y() - b.y()) for a, b in zip(positions, clamped))
                    if score < best_score:
                        best, best_score = clamped, score
        return best

    def toggle(self):
        if self.isVisible():
            self.hide()
            return
        self._style_buttons()
        rect = self.pet.frameGeometry()
        screen = QApplication.screenAt(rect.center()) or QApplication.primaryScreen()
        boxes = self._arrange(screen.availableGeometry())
        envelope = QRect(boxes[0])
        for box in boxes[1:]:
            envelope = envelope.united(box)
        self.setGeometry(envelope)
        mask = QRegion()
        for (key, _), box in zip(self.ACTIONS, boxes):
            local = box.translated(-envelope.topLeft())
            self.buttons[key].setGeometry(local)
            # A binary region must include the antialiased fringe, including
            # the thicker hover/focus border, instead of clipping it away.
            fringe = QRegion(local.adjusted(-2, -2, 2, 2), QRegion.Ellipse)
            mask = mask.united(fringe.intersected(QRegion(local)))
        # Only the buttons form the native popup; its transparent center does
        # not cover the cat or intercept clicks on the surrounding desktop.
        self.setMask(mask)
        self.show()
        self.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.pet and event.type() in (QEvent.Move, QEvent.Resize, QEvent.Hide):
            self.hide()
        return super().eventFilter(watched, event)
