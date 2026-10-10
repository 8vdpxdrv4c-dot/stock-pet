"""Tutorial pet: transparent PNG animation, dragging, and a right-click exit."""
import argparse
from pathlib import Path
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu, QWidget


ROOT = Path(__file__).resolve().parents[1]


class MinimalPet(QWidget):
    def __init__(self, frames_dir, interval_ms=100):
        super().__init__()
        self.setWindowTitle("我的第一只桌面宠物")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(240, 240)
        self.frames = []
        for path in sorted(Path(frames_dir).glob("idle_*.png")):
            frame = QPixmap(str(path))
            if not frame.isNull():
                self.frames.append(frame.scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
        if not self.frames:
            raise ValueError(f"没有可读取的 idle_*.png 帧：{frames_dir}")
        self.frame_index = 0
        self.drag_offset = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(interval_ms)
        bounds = QApplication.primaryScreen().availableGeometry()
        self.move(bounds.right() - self.width() - 19,
                  bounds.bottom() - self.height() - 19)

    def next_frame(self):
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        frame = self.frames[self.frame_index]
        painter.drawPixmap((self.width() - frame.width()) // 2,
                           (self.height() - frame.height()) // 2, frame)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        quit_action = menu.addAction("退出")
        if menu.exec_(event.globalPos()) == quit_action:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path,
                        default=ROOT / "assets/cat/sitting-idle")
    parser.add_argument("--fps", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.fps <= 60:
        parser.error("--fps 必须在 1 到 60 之间")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv[:1])
    try:
        pet = MinimalPet(args.frames, round(1000 / args.fps))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    pet.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
