import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from pet_widget import PetWidget


class EdgePeekTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_four_edges_and_return_to_desktop(self):
        pet = PetWidget()
        bounds = self.app.primaryScreen().availableGeometry()
        for edge in ("left", "right", "top", "bottom"):
            pet.move(bounds.center() - QPoint(pet.width() // 2, pet.height() // 2))
            pet._snap_to_edge(edge, bounds)
            pet._dock_after_drag(bounds.center())
            self.assertEqual(pet._dock_edge, edge)
            image = pet.grab().toImage()
            visible = sum(image.pixelColor(x, y).alpha() > 0
                          for x in range(image.width()) for y in range(image.height()))
            self.assertGreater(visible, 100)
            self.assertLess(visible, image.width() * image.height() // 3)
        pet.move(bounds.center() - QPoint(pet.width() // 2, pet.height() // 2))
        pet._dock_after_drag(bounds.center())
        self.assertIsNone(pet._dock_edge)
        pet.close()

    def test_click_preserves_peek_and_walk_restores_cat(self):
        pet = PetWidget()
        pet._set_dock_edge("left")
        clicks = []
        pet.clicked.connect(lambda: clicks.append(True))
        QTest.mouseClick(pet, Qt.LeftButton, pos=QPoint(15, 65))
        self.assertEqual(clicks, [True])
        self.assertEqual(pet._dock_edge, "left")
        pet.walk_to(pet.pos() + QPoint(50, 0))
        self.assertIsNone(pet._dock_edge)
        self.assertFalse(pet._peek_timer.isActive())
        pet.stop_walk()
        pet.close()

    def test_peek_animation_and_timer_lifecycle(self):
        pet = PetWidget()
        self.assertEqual(len(pet._peek_frames), 4)
        self.assertTrue(all(frame.size() == pet._peek_frames[0].size()
                            for frame in pet._peek_frames))
        self.assertFalse(pet._peek_timer.isActive())
        pet._set_dock_edge("left")
        self.assertTrue(pet._peek_timer.isActive())
        # Open -> half closed -> closed -> half closed -> open -> paw -> open.
        samples = [0, 2800, 2880, 3000, 3080, 5400, 5760, 8000]
        self.assertEqual([pet._peek_frame_index(ms) for ms in samples],
                         [0, 1, 2, 1, 0, 3, 0, 0])
        pet.start_sleeping()
        self.assertTrue(pet._peek_timer.isActive())
        pet._set_dock_edge(None)
        self.assertFalse(pet._peek_timer.isActive())
        self.assertFalse(pet._peek_clock.isValid())
        self.assertIs(pet._current_group(), pet._sleep_frames)
        pet.close()
