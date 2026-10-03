import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from pet_widget import PetWidget


class DragPlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.pet = PetWidget()
        bounds = self.app.primaryScreen().availableGeometry()
        self.pet.move(bounds.center() - QPoint(90, 80))
        self.origin = self.pet.pos() + QPoint(90, 80)

    def tearDown(self):
        self.pet._stop_drag_animation()
        self.pet._set_dock_edge(None)
        self.pet.close()

    def send_mouse(self, kind, global_pos, button, buttons):
        local = self.pet.mapFromGlobal(global_pos)
        event = QMouseEvent(kind, QPointF(local), QPointF(global_pos),
                            button, buttons, Qt.NoModifier)
        QApplication.sendEvent(self.pet, event)

    def start_drag(self):
        self.send_mouse(QEvent.MouseButtonPress, self.origin, Qt.LeftButton, Qt.LeftButton)
        self.send_mouse(QEvent.MouseMove, self.origin + QPoint(40, 0), Qt.NoButton, Qt.LeftButton)

    def test_only_actual_drag_triggers_loop(self):
        self.assertEqual(len(self.pet._drag_frames), 6)
        self.assertTrue(all(frame.cacheKey() in self.pet._scaled_frames
                            for frame in self.pet._drag_frames))
        self.assertFalse(self.pet._drag_timer.isActive())
        clicks = []
        self.pet.clicked.connect(lambda: clicks.append(True))
        self.send_mouse(QEvent.MouseButtonPress, self.origin, Qt.LeftButton, Qt.LeftButton)
        self.send_mouse(QEvent.MouseMove, self.origin + QPoint(1, 0), Qt.NoButton, Qt.LeftButton)
        self.assertFalse(self.pet._drag_animating)
        self.send_mouse(QEvent.MouseButtonRelease, self.origin, Qt.LeftButton, Qt.NoButton)
        self.assertEqual(clicks, [True])
        self.start_drag()
        self.assertTrue(self.pet._drag_animating)
        self.assertTrue(self.pet._drag_timer.isActive())
        QTest.qWait(120)
        self.assertGreater(self.pet._drag_frame_idx, 0)
        self.send_mouse(QEvent.MouseButtonRelease, self.origin + QPoint(40, 0), Qt.LeftButton, Qt.NoButton)
        self.assertFalse(self.pet._drag_animating)
        self.assertFalse(self.pet._drag_timer.isActive())
        self.assertEqual(clicks, [True])
        self.assertIsNone(self.pet._dock_edge)

    def test_sleep_state_restored_and_edge_release_peeks(self):
        self.pet.start_sleeping()
        self.start_drag()
        self.assertTrue(self.pet._drag_animating)
        self.assertTrue(self.pet._sleeping)
        bounds = self.app.primaryScreen().availableGeometry()
        drop = QPoint(bounds.left() + 90, bounds.center().y())
        self.send_mouse(QEvent.MouseMove, drop, Qt.NoButton, Qt.LeftButton)
        self.send_mouse(QEvent.MouseButtonRelease, drop, Qt.LeftButton, Qt.NoButton)
        self.assertFalse(self.pet._drag_animating)
        self.assertFalse(self.pet._drag_timer.isActive())
        self.assertEqual(self.pet._dock_edge, "left")
        self.assertTrue(self.pet._peek_timer.isActive())
        self.pet._set_dock_edge(None)
        self.assertIs(self.pet._current_group(), self.pet._sleep_frames)

    def test_dragging_out_of_edge_switches_to_play(self):
        self.pet._set_dock_edge("right")
        self.start_drag()
        self.assertIsNone(self.pet._dock_edge)
        self.assertFalse(self.pet._peek_timer.isActive())
        self.assertTrue(self.pet._drag_animating)
