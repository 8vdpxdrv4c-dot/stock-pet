import os
import json
import unittest
from statistics import median
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication
from pet_widget import PetWidget
from config import ASSETS_DIR


class EatingAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_video_frames_transparency_and_walk_resume(self):
        pet = PetWidget()
        try:
            folder = Path(ASSETS_DIR) / "cat/eating-video-v7"
            manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8"))
            pet.start_eating()
            self.assertEqual(pet._frame_timer.interval(), manifest["timer_interval_ms"])
            self.assertEqual(len(pet._eating_frames), manifest["frame_count"])
            self.assertEqual(pet._eating_frames[0].toImage(), QPixmap(str(folder / "idle_000.png")).toImage())
            self.assertNotEqual(pet._eating_frames[0].toImage(), pet._eating_frames[48].toImage())
            for frame in pet._eating_frames:
                image = frame.toImage()
                self.assertEqual([image.width(), image.height()], manifest["canvas_size"])
                # Transparent padding keeps the video background off the desktop.
                self.assertTrue(all(image.pixelColor(x, 0).alpha() == 0 and
                                    image.pixelColor(x, image.height() - 1).alpha() == 0
                                    for x in range(image.width())))
            pet.walk_to(pet.pos() + QPoint(20, 0))
            pet.stop_walk()
            self.assertIs(pet._current_group(), pet._eating_frames)
            self.assertEqual(pet._frame_timer.interval(), manifest["timer_interval_ms"])
        finally:
            pet.close()

    def test_eating_frames_have_no_opacity_flash_and_a_smooth_loop(self):
        pet = PetWidget()
        try:
            samples = []
            for frame in pet._eating_frames:
                image = frame.toImage()
                pixels = [image.pixelColor(x, y)
                          for y in range(4, image.height(), 8)
                          for x in range(4, image.width(), 8)]
                samples.append([(p.red(), p.green(), p.blue(), p.alpha() / 255)
                                for p in pixels])
            areas = [sum(p[3] for p in pixels) for pixels in samples]
            for i, area in enumerate(areas):
                self.assertGreater(area / len(samples[i]), .25, f"Empty/faded frame {i}")
                self.assertLess(abs(areas[(i + 1) % len(areas)] - area) / area, .08,
                                f"Opacity jump after frame {i}")
            for background in (32, 233):
                composited = [[channel * p[3] + background * (1 - p[3])
                               for p in pixels for channel in p[:3]] for pixels in samples]
                changes = [sum(abs(a - b) for a, b in zip(frame, composited[(i + 1) % len(samples)]))
                           / len(frame) for i, frame in enumerate(composited)]
                self.assertLess(changes[-1], median(changes[:-1]),
                                f"Visible loop jump on background {background}")
                brightness = [sum(frame) / len(frame) for frame in composited]
                for i, value in enumerate(brightness):
                    neighbour_mean = (brightness[i - 1] + brightness[(i + 1) % len(samples)]) / 2
                    self.assertLess(abs(value - neighbour_mean), 3,
                                    f"Isolated brightness flash at frame {i}")
        finally:
            pet.close()

    def test_front_legs_keep_their_opacity_in_every_frame(self):
        pet = PetWidget()
        try:
            folder = Path(ASSETS_DIR) / "cat/eating-video-v7"
            manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["solid_interior"])
            left, top, right, bottom = manifest["shared_crop"]
            size = manifest["canvas_size"][0]
            padding = manifest["padding"]
            scale = min((size - 2 * padding) / (right - left),
                        (size - 2 * padding) / (bottom - top))
            width, height = round((right - left) * scale), round((bottom - top) * scale)
            offset_x, offset_y = (size - width) // 2, size - padding - height
            # Reviewed source landmarks: three patches along the pale right
            # foreleg formerly cut out by the mask, plus both left paw patches.
            source_points = [(735, 1165), (755, 1190), (775, 1230),
                             (200, 1240), (225, 1260)]
            for index, frame in enumerate(pet._eating_frames):
                image = frame.toImage()
                for sx, sy in source_points:
                    px = round(offset_x + (sx - left) * scale)
                    py = round(offset_y + (sy - top) * scale)
                    for y in range(py - 2, py + 3):
                        for x in range(px - 2, px + 3):
                            colour = image.pixelColor(x, y)
                            self.assertGreaterEqual(colour.alpha(), 250,
                                                    f"Transparent leg at frame {index}: {x}, {y}")
        finally:
            pet.close()
