"""Animation switches must not stall the GUI."""
import os
import json
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from pet_widget import PetWidget
from config import ASSETS_DIR


class ResponsivenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_switches_use_prepared_assets_at_every_size(self):
        pet = PetWidget()
        try:
            manifest = json.loads((Path(ASSETS_DIR) / "cat/eating-video-v7/animation.json").read_text(encoding="utf-8"))
            for size in (50, 100, 300):
                pet.set_scale_percent(size)
                with patch.object(pet, "_load_action_frames", side_effect=AssertionError("disk read during action")):
                    for action, count in ((pet.start_sleeping, 16), (pet.start_eating, manifest["frame_count"]), (pet.start_idle, 8)):
                        action()
                        self.assertEqual(len(pet._current_group()), count)
                        for frame in pet._current_group():
                            self.assertIn(frame.cacheKey(), pet._scaled_frames)
                        pet.grab()
                self.assertFalse(pet._paint_timer.isActive())
        finally:
            pet.close()

    def test_png_does_not_repaint_thirty_times_per_second(self):
        class CountingPet(PetWidget):
            paints = 0

            def paintEvent(self, event):
                self.paints += 1
                super().paintEvent(event)

        pet = CountingPet()
        try:
            pet.show()
            QTest.qWait(40)
            pet.paints = 0
            QTest.qWait(450)
            self.assertGreaterEqual(pet.paints, 1)
            self.assertLessEqual(pet.paints, 5)
        finally:
            pet.close()


if __name__ == "__main__":
    unittest.main()
