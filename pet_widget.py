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
from PyQt5.QtCore import (Qt, QTimer, QElapsedTimer, QPoint, QPointF, QRectF, pyqtSignal)
from PyQt5.QtGui import (QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QPixmap, QMovie)
from PyQt5.QtWidgets import (QWidget, QMenu, QAction, QApplication)

from config import ASSETS_DIR
from idle_interaction import IdleInteraction

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
    open_settings_requested = pyqtSignal()
    empty_recycle_requested = pyqtSignal()
    focus_toggled = pyqtSignal(bool)

    PET_WIDTH = 180
    PET_HEIGHT = 160

    def __init__(self, pet_name: str = "小戒", scale_percent: int = 100):
        super().__init__()
        self.pet_name = pet_name
        self.scale_percent = max(50, min(300, int(scale_percent)))
        self._scaled_frames = {}
        self._opaque_bounds = {}
        self.mood = MOOD_NORMAL
        self._drag_pos = None
        self._click_origin = None
        self._dragged = False
        self._drag_animating = False
        self._drag_frame_idx = 0
        self._drag_frames = []
        drag_atlas = QPixmap(os.path.join(ASSETS_DIR, "cat", "drag-play-actions-v2.png"))
        if not drag_atlas.isNull():
            # Register each generated pose by its nose, not the atlas grid.
            # The atlas has uneven columns; grid slicing made the head jump.
            nose_anchors = [(273, 181), (624, 181), (977, 181),
                            (273, 800), (624, 800), (977, 800)]
            columns = [(70, 449), (449, 807), (807, 1170)]
            for index, (nose_x, nose_y) in enumerate(nose_anchors):
                left, right = columns[index % 3]
                top = nose_y - 180
                # The upper row's tail extends into the lower row's crop.
                # Clip that overlap without moving the nose or the ears.
                source_top = max(top, 634) if index >= 3 else top
                frame = QPixmap(418, 627)
                frame.fill(Qt.transparent)
                painter = QPainter(frame)
                painter.drawPixmap(209 - nose_x + left, source_top - top,
                                   drag_atlas.copy(left, source_top, right - left,
                                                   627 - (source_top - top)))
                painter.end()
                self._drag_frames.append(frame)
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(85)
        self._drag_timer.timeout.connect(self._on_drag_frame_tick)
        self._transforming = False
        self._transform_dock = None
        self._transform_base = QPixmap()
        self._transform_clock = QElapsedTimer()
        self._transform_timer = QTimer(self)
        self._transform_timer.setInterval(33)
        self._transform_timer.timeout.connect(self._on_transform_tick)
        self._transform_frames = []
        atlas = QPixmap(os.path.join(ASSETS_DIR, "cat", "transform-walk-sheet.png"))
        if not atlas.isNull():
            for index in range(8):
                row, column = divmod(index, 4)
                left, right = round(column * atlas.width() / 4), round((column + 1) * atlas.width() / 4)
                top, bottom = round(row * atlas.height() / 2), round((row + 1) * atlas.height() / 2)
                self._transform_frames.append(atlas.copy(left, top, right - left, bottom - top).scaled(
                    180, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._dock_edge = None
        self._peek_sprite = QPixmap(os.path.join(ASSETS_DIR, "cat", "edge-peek-v2.png"))
        if not self._peek_sprite.isNull():
            # The generated pose has a straight boundary at 5.2% of its canvas.
            inset = round(self._peek_sprite.width() * .052)
            self._peek_sprite = self._peek_sprite.copy(
                inset, 0, self._peek_sprite.width() - inset, self._peek_sprite.height())
        self._peek_frames = []
        atlas = QPixmap(os.path.join(ASSETS_DIR, "cat", "edge-peek-actions-v1.png"))
        if not atlas.isNull():
            cell_width, cell_height = atlas.width() // 2, atlas.height() // 2
            inset = round(cell_width * .078)
            for index in range(4):
                self._peek_frames.append(atlas.copy(
                    (index % 2) * cell_width + inset, (index // 2) * cell_height,
                    cell_width - inset, cell_height))
        self._peek_clock = QElapsedTimer()
        self._peek_timer = QTimer(self)
        self._peek_timer.setInterval(40)
        self._peek_timer.timeout.connect(self.update)
        self._sleeping = False
        self._eating = False
        self._eating_frames = []
        self._eating_interval = 200
        self._sleep_frames = []
        self._walk_frames = []
        self._walk_left_frames = []
        self._recycle_walk_frames = []
        self._recycle_walk_left_frames = []
        self._walk_for_recycle = False
        self._walk_faces_left = False
        self._focus_mode = False
        self._warning_flash = 0.0

        # 走动状态
        self._walking = False
        self._walk_timer = None
        self._walk_target = None
        self._walk_done = None

        # 帧状态
        self._frames = {}
        self._frame_idx = 0
        self._use_placeholder = False
        self._movie = None
        self._idle_interval = 200

        self._init_window()
        self._load_frames()
        self._warm_frame_cache()
        self._init_animation()
        self._idle_interaction = IdleInteraction(self)

    def showEvent(self, event):
        super().showEvent(event)
        self._idle_interaction.start()

    def hideEvent(self, event):
        self._idle_interaction.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._idle_interaction.stop()
        super().closeEvent(event)

    # ---------- 窗口 ----------
    def _init_window(self):
        self.setWindowTitle(f"{self.pet_name} · 桌面宠物")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(round(self.PET_WIDTH * self.scale_percent / 100),
                          round(self.PET_HEIGHT * self.scale_percent / 100))
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 19,
                  screen.bottom() - self.height() - 19)

    def set_scale_percent(self, value):
        value = max(50, min(300, int(value)))
        if value == self.scale_percent:
            return
        rect = self.frameGeometry()
        screen = QApplication.screenAt(rect.center()) or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        self.scale_percent = value
        self._scaled_frames.clear()
        self.setFixedSize(round(self.PET_WIDTH * value / 100),
                          round(self.PET_HEIGHT * value / 100))
        x = rect.center().x() - self.width() // 2
        y = rect.bottom() + 1 - self.height()
        x = max(bounds.left(), min(x, bounds.right() - self.width() + 1))
        y = max(bounds.top(), min(y, bounds.bottom() - self.height() + 1))
        self.move(x, y)
        if self._dock_edge:
            self._snap_to_edge(self._dock_edge, bounds)
        self._warm_frame_cache()
        self.update()

    def _warm_frame_cache(self):
        groups = list(self._frames.values()) + [self._eating_frames, self._sleep_frames,
                                               self._walk_frames, self._walk_left_frames,
                                               self._recycle_walk_frames, self._recycle_walk_left_frames,
                                               self._drag_frames]
        for group in groups:
            for pm in group:
                key = pm.cacheKey()
                if key not in self._scaled_frames:
                    self._scaled_frames[key] = pm.scaled(
                        self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _draw_frame(self, painter, original):
        key = original.cacheKey()
        pm = self._scaled_frames.get(key)
        if pm is None:
            pm = original.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if len(self._scaled_frames) >= 256:
                self._scaled_frames.clear()
            self._scaled_frames[key] = pm
        painter.drawPixmap((self.width() - pm.width()) // 2,
                           (self.height() - pm.height()) // 2, pm)

    def eating_body_center(self):
        """Visible cat center, excluding transparent canvas margins and the food bowl."""
        group = self._eating_frames or self._frames.get("idle", [])
        if not group:
            return QPointF(self.width() / 2, self.height() / 2)
        original = group[0]
        key = original.cacheKey()
        if key not in self._opaque_bounds:
            image = original.toImage()
            xs, ys = [], []
            # Upper 75% covers the cat's torso; the bowl sits below it.
            for y in range(int(image.height() * .75)):
                for x in range(image.width()):
                    if image.pixelColor(x, y).alpha() >= 160:
                        xs.append(x)
                        ys.append(y)
            self._opaque_bounds[key] = (QPointF((min(xs) + max(xs)) / 2,
                                                (min(ys) + max(ys)) / 2)
                                         if xs else QPointF(image.width() / 2, image.height() / 2))
        center = self._opaque_bounds[key]
        scaled = self._scaled_frames[key]
        return QPointF((self.width() - scaled.width()) / 2 + center.x() * scaled.width() / original.width(),
                       (self.height() - scaled.height()) / 2 + center.y() * scaled.height() / original.height())

    # ---------- 帧加载 ----------
    def _load_eating_animation(self, cat_dir):
        video_frames = self._load_action_frames(os.path.join(cat_dir, "eating-video-v7"))
        if video_frames:
            self._eating_interval = 33  # Source clip: 30 fps.
            return video_frames
        atlas = QPixmap(os.path.join(cat_dir, "eating-idle-v3-sheet.png"))
        if atlas.isNull():
            return []
        # Register the bowl bottom in each row before playing the head motion.
        row_bottoms = (306, 607, 920, 1224)
        row_starts = (0, 328, 625, 936)
        keys = []
        for index in range(16):
            row, column = divmod(index, 4)
            left = round(column * atlas.width() / 4)
            right = round((column + 1) * atlas.width() / 4)
            frame = QPixmap(320, 320)
            frame.fill(Qt.transparent)
            painter = QPainter(frame)
            top = row_bottoms[row] - 306
            start = row_starts[row]
            painter.drawPixmap((320 - (right - left)) // 2, start - top,
                               atlas.copy(left, start, right - left,
                                          row_bottoms[row] + 4 - start))
            painter.end()
            keys.append(frame)
        # Reverse the dipping poses to raise the head gently before chewing.
        sequence = (0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 9, 10, 11, 12, 13, 14, 15, 0)
        frames = []
        for position, index in enumerate(sequence):
            following = sequence[(position + 1) % len(sequence)]
            for step in range(4):
                if index == following or step == 0:
                    frames.append(keys[index])
                    continue
                frame = QPixmap(320, 320)
                frame.fill(Qt.transparent)
                painter = QPainter(frame)
                # Premultiplied additive blending keeps translucent fur opaque
                # and avoids alpha pulsing between nearby animation poses.
                painter.setCompositionMode(QPainter.CompositionMode_Plus)
                painter.setOpacity(1 - step / 4)
                painter.drawPixmap(0, 0, keys[index])
                painter.setOpacity(step / 4)
                painter.drawPixmap(0, 0, keys[following])
                painter.end()
                frames.append(frame)
        self._eating_interval = 50
        return frames

    def _load_action_frames(self, directory, prefix="idle_"):
        frames = []
        if os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                if name.startswith(prefix) and name.endswith(".png"):
                    pm = QPixmap(os.path.join(directory, name))
                    if not pm.isNull():
                        frames.append(pm)
        return frames

    def _load_frames(self):
        cat_dir = os.path.join(ASSETS_DIR, "cat")
        if not os.path.isdir(cat_dir):
            os.makedirs(cat_dir, exist_ok=True)
        self._eating_frames = self._load_eating_animation(cat_dir)
        if not self._eating_frames:
            self._eating_frames = self._load_action_frames(os.path.join(cat_dir, "eating-idle"))
        self._sleep_frames = self._load_action_frames(os.path.join(cat_dir, "sleep-idle"), "sleep_")
        self._walk_frames = self._load_action_frames(os.path.join(cat_dir, "walking-idle"), "walk_")
        self._walk_left_frames = [QPixmap.fromImage(pm.toImage().mirrored(True, False))
                                  for pm in self._walk_frames]
        self._recycle_walk_frames = self._load_action_frames(
            os.path.join(cat_dir, "recycle-walking-video"), "walk_")
        self._recycle_walk_left_frames = [QPixmap.fromImage(pm.toImage().mirrored(True, False))
                                         for pm in self._recycle_walk_frames]
        sitting_frames = self._load_action_frames(os.path.join(cat_dir, "sitting-idle"))
        if sitting_frames or self._eating_frames:
            self._frames = {"idle": sitting_frames or self._eating_frames}
            self._idle_interval = 50 if len(sitting_frames) >= 48 else 200
            logger.info("加载坐姿待机 %d 帧，吃饭 %d 帧",
                        len(sitting_frames), len(self._eating_frames))
            return
        gif_path = os.path.join(cat_dir, "idle.gif")
        if os.path.isfile(gif_path):
            movie = QMovie(gif_path, parent=self)
            if movie.isValid():
                self._movie = movie
                movie.frameChanged.connect(lambda _: self.update())
                movie.start()
                logger.info("加载默认 GIF: %s", gif_path)
                return
            logger.warning("默认 GIF 无法读取，回退 PNG 帧")
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
        if self._movie is None:
            self._frame_timer.start(self._idle_interval)

        self._bob_phase = 0.0
        self._paint_timer = QTimer(self)
        self._paint_timer.timeout.connect(self._on_paint_tick)
        # PNG frames repaint only when the frame changes; QMovie emits its own updates.
        # Continuous repainting is needed only for the procedural placeholder.
        if self._use_placeholder:
            self._paint_timer.start(33)

    def _current_group(self):
        if self._walking and self._walk_for_recycle and self._recycle_walk_frames:
            return self._recycle_walk_left_frames if self._walk_faces_left else self._recycle_walk_frames
        if self._walking and self._walk_frames:
            return self._walk_left_frames if self._walk_faces_left else self._walk_frames
        if self._sleeping:
            return self._sleep_frames
        if self._eating and self._eating_frames:
            return self._eating_frames
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
        self._bob_phase += 0.075 if self._walking else 0.04
        if self._warning_flash > 0:
            self._warning_flash = max(0.0, self._warning_flash - 0.03)
        self.update()

    # ---------- 走动 ----------
    def walk_to(self, target, on_arrive=None, recycle=False):
        """把窗口从当前位置'走'到 target。target 可以是 QPoint 或 (x, y)。

        每 16ms 挪一小步，步子带加减速（距离越近迈得越小），窗口在空中还会上下颠。
        """
        self._stop_transform(restore_dock=False)
        self.stop_walk()
        self._set_dock_edge(None)
        if hasattr(target, "x"):
            tx, ty = int(target.x()), int(target.y())
        else:
            tx, ty = int(target[0]), int(target[1])
        self._walk_target = QPoint(tx, ty)
        self._walk_position = QPointF(self.pos())
        self._walk_done = on_arrive
        self._walking = True
        self._walk_for_recycle = recycle
        self._walk_faces_left = tx < self.x()
        self._frame_idx = 0
        if self._movie is not None:
            self._movie.setPaused(True)
        self._frame_timer.start(42 if recycle and self._recycle_walk_frames else 100)
        if self._walk_timer is None:
            self._walk_timer = QTimer(self)
            self._walk_timer.timeout.connect(self._walk_tick)
        self._walk_timer.start(16)

    def _walk_tick(self):
        if self._walk_target is None:
            self.stop_walk()
            return
        cur = self._walk_position if self._walk_for_recycle else QPointF(self.pos())
        speed = 0.15 if self._walk_for_recycle else 1.0
        dx = self._walk_target.x() - cur.x()
        dy = self._walk_target.y() - cur.y()
        dist = max(abs(dx), abs(dy))
        if dist <= 6 * speed:
            self.move(self._walk_target)
            cb = self._walk_done
            self.stop_walk()
            if cb:
                cb()
            return
        step = min(max(4, dist // 8), 26)
        sx = step * dx / dist * speed if dx else 0
        sy = step * dy / dist * speed if dy else 0
        if not self._walk_for_recycle:
            sx, sy = round(sx), round(sy)
        # Keep fractional travel so the reduced speed remains smooth near arrival.
        self._walk_position = cur + QPointF(sx, sy)
        self.move(round(self._walk_position.x()), round(self._walk_position.y()))
        self.update()

    def stop_walk(self):
        """停下（到位、被用户打断、或退出时都调它）。不触发 on_arrive。"""
        self._walking = False
        self._walk_for_recycle = False
        self._walk_target = None
        self._walk_done = None
        if self._walk_timer is not None:
            self._walk_timer.stop()
        self._frame_timer.setInterval(200 if self._sleeping else
                                      self._eating_interval if self._eating else self._idle_interval)
        self._frame_idx = 0
        if self._movie is not None and not self._sleeping:
            self._frame_timer.stop()
            self._movie.setPaused(False)
        self.update()

    def is_walking(self):
        return self._walking

    # ---------- 对外 ----------
    def set_mood(self, mood: str, flash: bool = False):
        self.mood = mood
        self._frame_idx = 0
        if flash and mood in (MOOD_WARN, MOOD_PANIC):
            self._warning_flash = 1.0
        self.update()

    # ---------- 鼠标 ----------
    def _start_drag_animation(self):
        self._stop_transform(restore_dock=False)
        if self._drag_animating or not self._drag_frames:
            return
        self._drag_animating = True
        self._drag_frame_idx = 0
        self._drag_timer.start()
        self.update()

    def _stop_drag_animation(self):
        self._drag_animating = False
        self._drag_timer.stop()
        self._drag_frame_idx = 0
        self.update()

    def _on_drag_frame_tick(self):
        if self._drag_pos is None or not self._dragged:
            self._stop_drag_animation()
            return
        self._drag_frame_idx = (self._drag_frame_idx + 1) % len(self._drag_frames)
        self.update()

    def _set_dock_edge(self, edge):
        if edge == self._dock_edge:
            return
        self._dock_edge = edge
        if edge and self._peek_frames:
            self._peek_clock.start()
            self._peek_timer.start()
        else:
            self._peek_timer.stop()
            self._peek_clock.invalidate()
        self.update()

    def _peek_frame_index(self, elapsed_ms=None):
        """An eight-second idle: brief blink, then one gentle paw curl."""
        if elapsed_ms is None:
            elapsed_ms = self._peek_clock.elapsed() if self._peek_clock.isValid() else 0
        phase = elapsed_ms % 8000
        if 2800 <= phase < 2880 or 3000 <= phase < 3080:
            return 1
        if 2880 <= phase < 3000:
            return 2
        if 5400 <= phase < 5760:
            return 3
        return 0

    def _snap_to_edge(self, edge, bounds):
        x = max(bounds.left(), min(self.x(), bounds.right() - self.width() + 1))
        y = max(bounds.top(), min(self.y(), bounds.bottom() - self.height() + 1))
        if edge == "left":
            x = bounds.left()
        elif edge == "right":
            x = bounds.right() - self.width() + 1
        elif edge == "top":
            y = bounds.top()
        else:
            y = bounds.bottom() - self.height() + 1
        self.move(x, y)
        self.update()

    def _dock_after_drag(self, pointer):
        screen = QApplication.screenAt(pointer) or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        distances = {"left": self.x() - bounds.left(),
                     "right": bounds.right() + 1 - (self.x() + self.width()),
                     "top": self.y() - bounds.top(),
                     "bottom": bounds.bottom() + 1 - (self.y() + self.height())}
        edge = min(distances, key=distances.get)
        self._set_dock_edge(edge if distances[edge] <= 24 else None)
        if self._dock_edge:
            self._snap_to_edge(edge, bounds)
        else:
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._walking:
                self.stop_walk()   # 用户自己上手拖了，就别跟人家抢方向盘
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._click_origin = event.globalPos()
            self._dragged = False
            self._stop_drag_animation()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            if (event.globalPos() - self._click_origin).manhattanLength() >= QApplication.startDragDistance():
                self._dragged = True
                self._start_drag_animation()
                if self._dock_edge:
                    self._set_dock_edge(None)
                    self._drag_pos = QPoint(self.width() // 2, self.height() // 2)
                    self.update()
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self._drag_pos is not None:
            moved = (event.globalPos() - self._click_origin).manhattanLength()
            if not self._dragged and moved < QApplication.startDragDistance():
                self.clicked.emit()
            elif self._dragged:
                self._dock_after_drag(event.globalPos())
        self._drag_pos = None
        self._click_origin = None
        self._dragged = False
        self._stop_drag_animation()

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
            ("🐾 操作菜单", self.clicked.emit),
            ("🐱 恢复坐姿", self.start_idle),
            ("⚙️ 设置", self.open_settings_requested.emit),
            ("🗑️ 清空回收站", self.empty_recycle_requested.emit),
        ]:
            a = QAction(text, self)
            a.triggered.connect(slot)
            menu.addAction(a)
        focus_action = QAction("专注模式（暂缓提醒）", self)
        focus_action.setCheckable(True)
        focus_action.setChecked(self._focus_mode)
        focus_action.toggled.connect(self._toggle_focus)
        menu.addAction(focus_action)
        menu.addSeparator()
        act_quit = QAction("❌ 退出", self)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)
        menu.exec_(event.globalPos())

    def _toggle_focus(self, enabled):
        self._focus_mode = enabled
        self.focus_toggled.emit(enabled)

    # ---------- 绘制 ----------
    def start_transform(self):
        if not self._transform_frames:
            logger.warning("变身素材缺失")
            return
        if not self._transforming:
            if self._walking:
                self.stop_walk()
            group = self._current_group()
            self._transform_base = (group[self._frame_idx % len(group)] if group else
                                    self._movie.currentPixmap() if self._movie else QPixmap())
            self._transform_dock = self._dock_edge
            self._set_dock_edge(None)
        self._transforming = True
        self._transform_clock.start()
        self._transform_timer.start()
        self.update()

    def _stop_transform(self, restore_dock=True):
        if not self._transforming:
            return
        self._transforming = False
        self._transform_timer.stop()
        self._transform_clock.invalidate()
        if restore_dock and self._transform_dock:
            self._set_dock_edge(self._transform_dock)
        self._transform_dock = None
        self.update()

    def _on_transform_tick(self):
        if self._transform_clock.elapsed() >= 4800:
            self._stop_transform()
        else:
            self.update()

    def _draw_transform(self, p, elapsed_ms=None):
        elapsed = self._transform_clock.elapsed() if elapsed_ms is None else elapsed_ms
        fraction = max(0.0, min(1.0, elapsed / 800, (4800 - elapsed) / 800))
        spread = fraction * fraction * (3 - 2 * fraction)
        p.save()
        p.scale(self.width() / 180, self.height() / 160)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        poses = ((-54, -26, 68), (-18, -34, 68), (18, -34, 68), (54, -26, 68),
                 (-32, 2, 82), (32, 2, 82), (0, 22, 94))
        for index, (dx, dy, size) in enumerate(poses):
            central = index == len(poses) - 1
            p.setOpacity(1 if central else spread)
            side = 160 + (size - 160) * spread
            bob = math.sin(elapsed / 170 + index) * .7 * spread
            target = QRectF(90 + dx * spread - side / 2,
                            80 + dy * spread + bob - side / 2, side, side)
            pm = self._transform_frames[(elapsed // 100 + index) % len(self._transform_frames)]
            if central and not self._transform_base.isNull():
                p.setOpacity(1 - spread)
                p.drawPixmap(target, self._transform_base, QRectF(self._transform_base.rect()))
                p.setOpacity(spread)
            p.drawPixmap(target, pm, QRectF(pm.rect()))
        p.restore()

    def start_idle(self):
        self._stop_transform(restore_dock=False)
        self._sleeping = False
        self._eating = False
        self._frame_idx = 0
        if self._movie is None:
            self._frame_timer.start(self._idle_interval)
        else:
            self._frame_timer.stop()
        if self._movie is not None:
            self._movie.start()
        self.update()

    def animation_state(self):
        return {"action": "sleep" if self._sleeping else "eat" if self._eating else "idle",
                "mood": self.mood, "frame": self._frame_idx}

    def restore_animation_state(self, state):
        {"sleep": self.start_sleeping, "eat": self.start_eating,
         "idle": self.start_idle}[state["action"]]()
        self.set_mood(state["mood"])
        self._frame_idx = state["frame"] % max(1, len(self._current_group()))
        self.update()

    def start_eating(self):
        self._stop_transform(restore_dock=False)
        self._sleeping = False
        self._eating = bool(self._eating_frames)
        self._frame_idx = 0
        if self._movie is None:
            self._frame_timer.start(self._eating_interval)
        else:
            self._frame_timer.stop()
        if self._movie is not None:
            self._movie.start()
        self.update()

    def start_sleeping(self):
        self._stop_transform(restore_dock=False)
        if not self._sleep_frames:
            logger.warning("睡觉帧缺失，保留当前动画")
            return
        self._sleeping = True
        self._eating = False
        self._frame_idx = 0
        self._frame_timer.start(200)
        if self._movie is not None:
            self._movie.setPaused(True)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self._transforming:
            self._draw_transform(p)
            p.end()
            return
        if self._drag_animating and self._drag_frames:
            self._draw_frame(p, self._drag_frames[self._drag_frame_idx])
            p.end()
            return
        if self._dock_edge and not self._walking:
            self._draw_edge_peek(p)
            p.end()
            return

        group = self._current_group()
        if self._idle_interaction.enabled() and group:
            self._idle_interaction.draw(p, group[self._frame_idx % len(group)])
        elif ((self._walking and self._walk_frames) or self._sleeping) and group:
            pm = group[self._frame_idx % len(group)]
            self._draw_frame(p, pm)
        elif self._movie is not None:
            self._draw_frame(p, self._movie.currentPixmap())
        elif group:
            pm = group[self._frame_idx % len(group)]
            self._draw_frame(p, pm)
        else:
            p.scale(self.width() / self.PET_WIDTH, self.height() / self.PET_HEIGHT)
            self._draw_placeholder_cat(p)

        p.end()

    def _draw_edge_peek(self, p):
        """Draw a coherent tilted head and dangling paw at the desktop boundary."""
        edge = self._dock_edge
        anchors = {"left": (0, self.height() / 2, 0),
                   "right": (self.width(), self.height() / 2, 0),
                   "top": (self.width() / 2, 0, 90),
                   "bottom": (self.width() / 2, self.height(), -90)}
        x, y, angle = anchors[edge]
        p.translate(x, y)
        p.rotate(angle)
        if edge == "right":
            p.scale(-1, 1)
        scale = min(self.width(), self.height()) / 160
        p.scale(scale, scale)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        source = (self._peek_frames[self._peek_frame_index()]
                  if self._peek_frames else self._peek_sprite)
        if not source.isNull():
            height = 140
            width = height * source.width() / source.height()
            p.drawPixmap(QRectF(0, -height / 2, width, height), source,
                         QRectF(source.rect()))
        else:
            p.setPen(QPen(QColor(180, 110, 60), 1.5))
            p.setBrush(QColor(255, 180, 110))
            p.drawEllipse(QRectF(-44, -44, 88, 76))
            p.drawEllipse(QRectF(-5, 34, 30, 23))
            p.setBrush(QColor(35, 28, 20))
            p.drawEllipse(QRectF(12, -15, 12, 18))

    # ---------- 占位橘猫 ----------
    def _draw_placeholder_cat(self, p):
        w, h = self.PET_WIDTH, self.PET_HEIGHT
        cx = w / 2
        bob = -abs((3.6 if self._walking else 2.5) * math.sin(self._bob_phase))

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
