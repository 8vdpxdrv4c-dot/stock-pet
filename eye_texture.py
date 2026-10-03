"""Deform the user's photographed eye without synthesizing iris colors."""
import math
from collections import OrderedDict

from PyQt5.QtGui import QImage, QPixmap


class EyeTexture:
    def __init__(self, path):
        self.source = QImage(path).convertToFormat(QImage.Format_RGBA8888)
        self.cache = OrderedDict()
        self.size = 64
        if not self.source.isNull():
            bits = self.source.bits()
            bits.setsize(self.source.byteCount())
            self.pixels = bytes(bits)
            self.stride = self.source.bytesPerLine()

    def frame(self, gaze):
        if self.source.isNull():
            return QPixmap()
        key = (round(gaze.x() * 20), round(gaze.y() * 20))
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        shift_x, shift_y = key[0] / 20 * .38, key[1] / 20 * .34
        size = self.size
        rgba = bytearray(size * size * 4)
        # Measured ellipse inside the supplied 104x104 eye photo.
        cx, cy = self.source.width() * 56 / 104, self.source.height() * 55 / 104
        rx, ry = self.source.width() * 32 / 104, self.source.height() * 29 / 104
        for y in range(size):
            ty = (y + .5) * 2 / size - 1
            for x in range(size):
                tx = (x + .5) * 2 / size - 1
                radius = math.hypot(tx, ty)
                coverage = min(1.0, max(0.0, (1 - radius) * size / 2 + .5))
                if not coverage:
                    continue
                # Invert an anchored radial deformation. At the eyelid the
                # displacement is zero; the pupil moves while the iris stretches.
                sx, sy = tx, ty
                for _ in range(7):
                    weight = max(0.0, 1 - sx * sx - sy * sy) ** 2
                    sx, sy = tx - shift_x * weight, ty - shift_y * weight
                px = max(0, min(self.source.width() - 1.001, cx + sx * rx))
                py = max(0, min(self.source.height() - 1.001, cy + sy * ry))
                ix, iy = int(px), int(py)
                fx, fy = px - ix, py - iy
                positions = (iy * self.stride + ix * 4, iy * self.stride + (ix + 1) * 4,
                             (iy + 1) * self.stride + ix * 4, (iy + 1) * self.stride + (ix + 1) * 4)
                weights = ((1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy)
                out = (y * size + x) * 4
                for channel in range(3):
                    rgba[out + channel] = round(sum(self.pixels[pos + channel] * w
                                                     for pos, w in zip(positions, weights)))
                rgba[out + 3] = round(255 * coverage)
        image = QImage(bytes(rgba), size, size, size * 4, QImage.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(image)
        self.cache[key] = pixmap
        if len(self.cache) > 128:
            self.cache.popitem(last=False)
        return pixmap
