"""桌面宠物主窗口：猫形逐帧动画。

帧目录约定（assets/cat/）：
  idle_0.png idle_1.png ...     待机循环
  warn_0.png  warn_1.png ...    警告
  panic_0.png panic_1.png ...   恐慌
  happy_0.png happy_1.png ...  开心

目录里没图时，用 QPainter 画一只占位橘猫。
"""
import logging
import math
import os
from PyQt5.QtCore import (Qt, QTimer, QPoint, QPointF, QRectF, pyqtSignal)
from PyQt5.QtGui import (QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QPixmap)
from PyQt5.QtWidgets import (QWidget, QMenu, QAction, QApplication)

from config import ASSETS_DIR

logger = logging.getLogger(__name__)

MOOD_NORMAL = "normal"
MOOD_WARN = "warn"
MOOD_PANIC = "panic"
MOOD_HAPPY = "happy"

# mood -> 帧前缀
_MOOD_TO_PREFIX = {
    MOOD_NORMAL: "idle",
    MOOD_WARN: "warn",
    MOOD_PANIC: "panic",
    MOOD_HAPPY: "happy",
}


class PetWidget(QWidget):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    quit_requested = pyqtSignal()
    pause_toggled = pyqtSignal(bool)
    open_settings_requested = pyqtSignal()

    PET_WIDTH = 180
    PET_HEIGHT = 160

    def __init__(self, pet_name: str = "小戒"):
        super().__init__()
        self.pet_name = pet_name
        self.mood = MOOD_NORMAL
        self._drag_pos = None
        self._paused = False
        self._warning_flash = 0.0

        # 帧状态
        self._frames = {}
        self._frame_idx = 0
        self._use_placeholder = False

        self._init_window()
        self._load_frames()
        self._init_animation()

    # ---------- 窗口 ----------
    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(self.PET_WIDTH, self.PET_HEIGHT)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.PET_WIDTH - 20,
                  screen.height() - self.PET_HEIGHT - 20)

    # ---------- 帧加载 ----------
    def _load_frames(self):
        cat_dir = os.path.join(ASSETS_DIR, "cat")
        if not os.path.isdir(cat_dir):
            os.makedirs(cat_dir, exist_ok=True)
        self._restore_frames_from_b64(cat_dir)

        # 扫描 idle_*.png / warn_*.png / ...
        groups = {}
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.lower().endswith(".png"):
                continue
            stem = os.path.splitext(fname)[0]
            if "_" not in stem:
                continue
            prefix = stem.split("_", 1)[0]
            groups.setdefault(prefix, []).append(os.path.join(cat_dir, fname))

        if not groups:
            self._use_placeholder = True
            logger.info("assets/cat/ 是空目录，用占位猫绘制")
            return

        self._frames = {}
        for prefix, paths in groups.items():
            pixmaps = []
            for p in paths:
                pm = QPixmap(p)
                if not pm.isNull():
                    pm = pm.scaled(self.PET_WIDTH, self.PET_HEIGHT,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    pixmaps.append(pm)
            if pixmaps:
                self._frames[prefix] = pixmaps
                logger.info("加载帧组 %s: %d 帧", prefix, len(pixmaps))

        # 至少要有 idle 组，否则退回占位
        if "idle" not in self._frames:
            logger.warning("assets/cat/ 里没有 idle_*.png，退回占位猫")
            self._use_placeholder = True

    def _restore_frames_from_b64(self, cat_dir: str):
        """GitHub 无法存二进制 PNG，仓库里带 *.png.b64.txt 文本。
        本地缺失 PNG 时自动解码还原。"""
        import base64
        try:
            names = os.listdir(cat_dir)
        except OSError:
            return
        for fname in names:
            if not fname.endswith(".b64.txt"):
                continue
            target_png = fname[:-len(".b64.txt")]
            if not target_png.lower().endswith(".png"):
                continue
            if os.path.exists(os.path.join(cat_dir, target_png)):
                continue
            try:
                with open(os.path.join(cat_dir, fname), "r", encoding="ascii") as f:
                    data = base64.b64decode(f.read())
                with open(os.path.join(cat_dir, target_png), "wb") as f:
                    f.write(data)
                logger.info("从 %s 还原 %s", fname, target_png)
            except Exception as e:
                logger.warning("还原 %s 失败: %s", fname, e)

    # ---------- 动画 ----------
    def _init_animation(self):
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._on_frame_tick)
        # 有自定义帧时用帧图的节奏；占位猫用 200ms 切表情
        self._frame_timer.start(200)

        self._bob_phase = 0.0
        self._paint_timer = QTimer(self)
        self._paint_timer.timeout.connect(self._on_paint_tick)
        self._paint_timer.start(33)

    def _current_group(self):
        prefix = _MOOD_TO_PREFIX.get(self.mood, "idle")
        if self._use_placeholder:
            return []
        return self._frames.get(prefix) or self._frames.get("idle", [])

    def _on_frame_tick(self):
        group = self._current_group()
        if group:
            self._frame_idx = (self._frame_idx + 1) % len(group)
        # 占位猫模式下 frame_idx 用来切换眨眼
        else:
            self._frame_idx = (self._frame_idx + 1) % 4
        self.update()

    def _on_paint_tick(self):
        self._bob_phase += 0.04
        if self._warning_flash > 0:
            self._warning_flash = max(0.0, self._warning_flash - 0.03)
        self.update()

    # ---------- 对外 ----------
    def set_mood(self, mood: str, flash: bool = False):
        self.mood = mood
        self._frame_idx = 0
        if flash and mood in (MOOD_WARN, MOOD_PANIC):
            self._warning_flash = 1.0
        self.update()

    def is_paused(self) -> bool:
        return self._paused

    # ---------- 鼠标 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_pos is not None:
            moved = (event.globalPos() - (self.frameGeometry().topLeft() + self._drag_pos)).manhattanLength()
            if moved < 5:
                self.clicked.emit()
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#fff;color:#333;border:1px solid #ccc;padding:4px;}"
            "QMenu::item{padding:6px 20px;border-radius:4px;}"
            "QMenu::item:selected{background:#ffe4c4;}"
        )
        for text, slot in [
            ("💬 打开聊天", self.clicked.emit),
            ("⚙️ 设置", self.open_settings_requested.emit),
        ]:
            a = QAction(text, self)
            a.triggered.connect(slot)
            menu.addAction(a)
        act_pause = QAction("⏸ 暂停提醒" if not self._paused else "▶ 恢复提醒", self)
        act_pause.triggered.connect(self._toggle_pause)
        menu.addAction(act_pause)
        menu.addSeparator()
        act_quit = QAction("❌ 退出", self)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)
        menu.exec_(event.globalPos())

    def _toggle_pause(self):
        self._paused = not self._paused
        self.pause_toggled.emit(self._paused)

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        group = self._current_group()
        if group:
            pm = group[self._frame_idx % len(group)]
            p.drawPixmap(0, 0, pm)
        else:
            self._draw_placeholder_cat(p)

        p.end()

    # ---------- 占位橘猫 ----------
    def _draw_placeholder_cat(self, p):
        w, h = self.PET_WIDTH, self.PET_HEIGHT
        cx = w / 2
        bob = -abs(2.5 * math.sin(self._bob_phase))

        # 警告光晕
        if self.mood == MOOD_PANIC:
            p.setBrush(QColor(255, 80, 80, int(60 + 80 * self._warning_flash)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(10, 10 + bob, w - 20, h - 20))
        elif self.mood == MOOD_WARN:
            p.setBrush(QColor(255, 200, 80, int(60 + 60 * self._warning_flash)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(10, 10 + bob, w - 20, h - 20))

        # 颜色
        if self.mood == MOOD_PANIC:
            fur = QColor(255, 150, 120)
        elif self.mood == MOOD_WARN:
            fur = QColor(255, 200, 130)
        elif self.mood == MOOD_HAPPY:
            fur = QColor(255, 210, 160)
        else:
            fur = QColor(255, 180, 110)  # 橘猫

        # 身体
        p.setBrush(QBrush(fur))
        p.setPen(QPen(QColor(180, 110, 60), 1.5))
        body_cy = 145 + bob
        p.drawEllipse(QPointF(cx, body_cy), 45, 32)

        # 尾巴（frame_idx 决定摇摆方向）
        tail_pen = QPen(fur, 8)
        tail_pen.setCapStyle(Qt.RoundCap)
        p.setPen(tail_pen)
        tail_swing = 15 if self._frame_idx % 2 == 0 else -10
        p.drawLine(QPointF(cx + 40, body_cy + 5),
                   QPointF(cx + 55 + tail_swing, body_cy - 15))

        # 头
        head_cy = 85 + bob
        head_r = 38
        p.setBrush(QBrush(fur))
        p.setPen(QPen(QColor(180, 110, 60), 1.5))
        p.drawEllipse(QPointF(cx, head_cy), head_r, head_r)

        # 耳朵
        p.setBrush(QBrush(fur))
        left_ear = QPainterPath()
        left_ear.moveTo(cx - head_r + 5, head_cy - 20)
        left_ear.lineTo(cx - head_r + 12, head_cy - head_r - 8)
        left_ear.lineTo(cx - head_r + 25, head_cy - 22)
        left_ear.closeSubpath()
        p.drawPath(left_ear)
        right_ear = QPainterPath()
        right_ear.moveTo(cx + head_r - 5, head_cy - 20)
        right_ear.lineTo(cx + head_r - 12, head_cy - head_r - 8)
        right_ear.lineTo(cx + head_r - 25, head_cy - 22)
        right_ear.closeSubpath()
        p.drawPath(right_ear)
        # 耳朵内侧
        p.setBrush(QBrush(QColor(255, 180, 180)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx - head_r + 16, head_cy - 30), 4, 6)
        p.drawEllipse(QPointF(cx + head_r - 16, head_cy - 30), 4, 6)

        # 眼睛
        eye_y = head_cy - 2
        eye_dx = 15
        blink = (self._frame_idx % 4 == 1) or (self._frame_idx % 4 == 3)
        if self.mood == MOOD_HAPPY:
            p.setPen(QPen(QColor(60, 40, 30), 2))
            p.drawArc(QRectF(cx - eye_dx - 5, eye_y - 6, 10, 10), 0, -180 * 16)
            p.drawArc(QRectF(cx + eye_dx - 5, eye_y - 6, 10, 10), 0, -180 * 16)
        elif self.mood == MOOD_PANIC:
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(QColor(60, 40, 30), 1.5))
            p.drawEllipse(QPointF(cx - eye_dx, eye_y), 7, 8)
            p.drawEllipse(QPointF(cx + eye_dx, eye_y), 7, 8)
            p.setBrush(QBrush(QColor(200, 40, 40)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx - eye_dx, eye_y), 3, 4)
            p.drawEllipse(QPointF(cx + eye_dx, eye_y), 3, 4)
        elif self.mood == MOOD_WARN:
            p.setPen(QPen(QColor(60, 40, 30), 2))
            p.drawLine(QPointF(cx - eye_dx - 5, eye_y - 4), QPointF(cx - eye_dx + 5, eye_y + 2))
            p.drawLine(QPointF(cx + eye_dx + 5, eye_y - 4), QPointF(cx + eye_dx - 5, eye_y + 2))
        elif blink:
            p.setPen(QPen(QColor(60, 40, 30), 2))
            p.drawLine(int(cx - eye_dx - 5), int(eye_y), int(cx - eye_dx + 5), int(eye_y))
            p.drawLine(int(cx + eye_dx - 5), int(eye_y), int(cx + eye_dx + 5), int(eye_y))
        else:
            p.setBrush(QBrush(QColor(60, 40, 30)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx - eye_dx, eye_y), 3.5, 4.5)
            p.drawEllipse(QPointF(cx + eye_dx, eye_y), 3.5, 4.5)
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(QPointF(cx - eye_dx + 1, eye_y - 1.5), 1.2, 1.2)
            p.drawEllipse(QPointF(cx + eye_dx + 1, eye_y - 1.5), 1.2, 1.2)

        # 鼻子
        p.setBrush(QBrush(QColor(255, 150, 150)))
        p.setPen(Qt.NoPen)
        nose = QPainterPath()
        nose.moveTo(cx - 3, head_cy + 8)
        nose.lineTo(cx + 3, head_cy + 8)
        nose.lineTo(cx, head_cy + 11)
        nose.closeSubpath()
        p.drawPath(nose)

        # 嘴
        p.setPen(QPen(QColor(120, 70, 50), 1.5))
        p.setBrush(Qt.NoBrush)
        if self.mood == MOOD_PANIC:
            p.setBrush(QBrush(QColor(180, 60, 60)))
            p.drawEllipse(QPointF(cx, head_cy + 18), 4, 5)
        elif self.mood == MOOD_HAPPY:
            p.drawArc(QRectF(cx - 8, head_cy + 10, 8, 6), 0, -180 * 16)
            p.drawArc(QRectF(cx, head_cy + 10, 8, 6), 0, -180 * 16)
        elif self.mood == MOOD_WARN:
            p.drawLine(int(cx - 5), int(head_cy + 15), int(cx + 5), int(head_cy + 15))
        else:
            p.drawArc(QRectF(cx - 6, head_cy + 10, 6, 6), 0, -180 * 16)
            p.drawArc(QRectF(cx, head_cy + 10, 6, 6), 0, -180 * 16)

        # 腮红
        p.setBrush(QColor(255, 150, 150, 150))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx - 25, head_cy + 10), 5, 3)
        p.drawEllipse(QPointF(cx + 25, head_cy + 10), 5, 3)

        # 名字
        p.setPen(QPen(QColor(100, 100, 100), 1))
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(QRectF(0, h - 18, w, 16), Qt.AlignHCenter, self.pet_name)
