import os
import unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QPoint
from PyQt5.QtTest import QTest
from pet_widget import PetWidget


class WalkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_direction_cached_frames_and_arrival(self):
        pet = PetWidget()
        pet.start_sleeping()
        original = pet.animation_state()
        self.assertEqual(len(pet._walk_frames), 8)
        self.assertTrue(all(frame.cacheKey() in pet._scaled_frames for frame in pet._walk_left_frames))
        destination = pet.pos() - QPoint(24, 0)
        arrived = []
        pet.walk_to(destination, lambda: arrived.append(True))
        self.assertIs(pet._current_group(), pet._walk_left_frames)
        for _ in range(100):
            QTest.qWait(10)
            if arrived:
                break
        self.assertEqual(arrived, [True])
        self.assertEqual(pet.pos(), destination)
        self.assertIs(pet._current_group(), pet._sleep_frames)
        pet.walk_to(destination + QPoint(24, 0))
        self.assertIs(pet._current_group(), pet._walk_frames)
        pet.stop_walk()
        pet.restore_animation_state(original)
        self.assertEqual(pet.animation_state(), original)
        pet.close()

    def test_recycle_video_both_directions_and_restore(self):
        pet = PetWidget()
        try:
            self.assertEqual(len(pet._recycle_walk_frames), 97)
            self.assertTrue(all(frame.cacheKey() in pet._scaled_frames
                                for frame in pet._recycle_walk_left_frames))
            pet.start_eating()
            destination = pet.pos() - QPoint(24, 0)
            arrived = []
            pet.walk_to(destination, lambda: arrived.append(True), recycle=True)
            self.assertIs(pet._current_group(), pet._recycle_walk_left_frames)
            self.assertEqual(pet._frame_timer.interval(), 42)
            for _ in range(100):
                QTest.qWait(10)
                if arrived:
                    break
            self.assertEqual(arrived, [True])
            self.assertIs(pet._current_group(), pet._eating_frames)
            pet.walk_to(destination + QPoint(24, 0), recycle=True)
            self.assertIs(pet._current_group(), pet._recycle_walk_frames)
            pet.stop_walk()
            self.assertEqual(pet._frame_timer.interval(), pet._eating_interval)
        finally:
            pet.close()
