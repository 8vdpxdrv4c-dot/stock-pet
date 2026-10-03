"""Small native-rendered gaze and paw motions using the existing sitting art."""
import math
import os

from PyQt5.QtCore import QObject, QPointF, QRectF, QElapsedTimer, QTimer
from PyQt5.QtGui import QCursor, QPainter, QPainterPath

from keyboard_input import KeyboardInput
from eye_texture import EyeTexture
from config import ASSETS_DIR


class IdleInteraction(QObject):
    def __init__(self, pet):
        super().__init__(pet)
        self.pet = pet
        self.gaze = QPointF()
        self.eyes = EyeTexture(os.path.join(ASSETS_DIR, "cat", "eye-reference.png"))
        self.tap_clock = QElapsedTimer()
        self.keyboard = KeyboardInput(self)
        self.keyboard.key_pressed.connect(self.tap)
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.tick)

    def enabled(self):
        pet = self.pet
        return (not any((pet._sleeping, pet._eating, pet._walking, pet._drag_animating,
                         pet._transforming, pet._dock_edge, pet._movie))
                and bool(pet._frames.get("idle")))

    def start(self):
        self.keyboard.start(self.pet.winId())
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.keyboard.stop()
        self.tap_clock.invalidate()

    def tap(self):
        if self.pet.isVisible() and self.enabled():
            self.tap_clock.start()  # Every key down retriggers the same paw.
            self.pet.update()

    def tick(self):
        if not self.pet.isVisible() or not self.enabled():
            self.tap_clock.invalidate()
            return
        side = min(self.pet.width(), self.pet.height())
        origin = self.pet.mapToGlobal(self.pet.rect().topLeft())
        eye_x = origin.x() + self.pet.width() / 2
        eye_y = origin.y() + (self.pet.height() - side) / 2 + side * 126 / 443
        mouse = QCursor.pos()
        # Normalize the vector as a whole: independent axis clamps froze the
        # gaze whenever the cursor was far away in the same screen quadrant.
        dx, dy = mouse.x() - eye_x, mouse.y() - eye_y
        distance = math.sqrt(dx * dx + dy * dy + 45 * 45)
        x, y = dx / distance, dy / distance
        if abs(x - self.gaze.x()) + abs(y - self.gaze.y()) > .002:
            self.gaze = QPointF(x, y)
            self.pet.update()
        if self.tap_clock.isValid():
            self.pet.update()
            if self.tap_clock.elapsed() >= 160:
                self.tap_clock.invalidate()

    def paw_lift(self):
        if not self.tap_clock.isValid():
            return 0.0
        phase = min(1.0, self.tap_clock.elapsed() / 160)
        return 16 * math.sin(math.pi * phase)

    def draw(self, painter, source):
        pet = self.pet
        side = min(pet.width(), pet.height())
        painter.save()
        painter.translate((pet.width() - side) / 2, (pet.height() - side) / 2)
        painter.scale(side / 443, side / 443)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        canvas = QRectF(0, 0, 443, 443)
        paw = QRectF(146, 348, 72, 94)
        lift = self.paw_lift()
        painter.save()
        if lift > .01:
            body = QPainterPath()
            body.addRect(canvas)
            cutout = QPainterPath()
            cutout.addRect(paw)
            painter.setClipPath(body.subtracted(cutout))
        painter.drawPixmap(canvas, source, QRectF(source.rect()))
        painter.restore()
        if lift > .01:
            src = QRectF(paw.x() * source.width() / 443, paw.y() * source.height() / 443,
                         paw.width() * source.width() / 443, paw.height() * source.height() / 443)
            painter.drawPixmap(QRectF(paw.x(), paw.y(), paw.width(), paw.height() - lift), source, src)
        eye_frame = self.eyes.frame(self.gaze)
        for eye in (QRectF(158, 108, 41, 36), QRectF(239, 108, 41, 36)):
            if eye_frame.isNull():
                continue
            painter.save()
            socket = QPainterPath()
            socket.addEllipse(eye)
            painter.setClipPath(socket)
            painter.drawPixmap(eye, eye_frame, QRectF(eye_frame.rect()))
            painter.restore()
        painter.restore()
