import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from pet_widget import PetWidget
from pet_actions import PetActions


class TransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.pet = PetWidget()

    def tearDown(self):
        self.pet._stop_transform()
        self.pet._stop_drag_animation()
        self.pet._set_dock_edge(None)
        self.pet.close()

    def test_button_and_completion_restore_sleep_and_edge(self):
        self.pet.start_sleeping()
        self.pet._set_dock_edge("left")
        menu = PetActions(self.pet)
        requested = []
        menu.action_requested.connect(requested.append)
        menu.action_requested.connect(lambda action: self.pet.start_transform() if action == "transform" else None)
        QTest.mouseClick(menu.buttons["transform"], Qt.LeftButton)
        self.assertEqual(requested, ["transform"])
        self.assertTrue(self.pet._transforming)
        self.assertEqual(len(self.pet._transform_frames), 8)
        self.assertIsNone(self.pet._dock_edge)
        self.pet.start_transform()  # Repeated clicks retain the original restore state.
        with patch.object(self.pet._transform_clock, "elapsed", return_value=4800):
            self.pet._on_transform_tick()
        self.assertFalse(self.pet._transforming)
        self.assertFalse(self.pet._transform_timer.isActive())
        self.assertEqual(self.pet._dock_edge, "left")
        self.assertIs(self.pet._current_group(), self.pet._sleep_frames)
        menu.close()

    def test_actions_and_drag_cancel_transform(self):
        self.pet.start_transform()
        self.pet.start_eating()
        self.assertFalse(self.pet._transforming)
        self.assertIs(self.pet._current_group(), self.pet._eating_frames)
        self.pet.start_transform()
        self.pet._start_drag_animation()
        self.assertFalse(self.pet._transforming)
        self.assertTrue(self.pet._drag_animating)

    def test_group_is_larger_and_restores_original_geometry(self):
        original = self.pet.geometry()
        self.pet.start_transform()
        self.assertEqual(self.pet.size(), QSize(270, 240))
        self.assertEqual(self.pet.scale_percent, 100)
        expanded = self.pet.geometry()
        self.pet.start_transform()
        self.assertEqual(self.pet.geometry(), expanded)
        with patch.object(self.pet._transform_clock, "elapsed", return_value=4800):
            self.pet._on_transform_tick()
        self.assertEqual(self.pet.geometry(), original)
        self.assertIsNone(self.pet._transform_geometry)

    def test_expanded_group_stays_on_screen_and_scale_changes_restore(self):
        bounds = self.app.primaryScreen().availableGeometry()
        for scale in (50, 100, 300):
            self.pet.set_scale_percent(scale)
            for position in (bounds.topLeft(), bounds.bottomRight() - QPoint(self.pet.width() - 1, self.pet.height() - 1)):
                self.pet.move(position)
                original = self.pet.geometry()
                self.pet.start_transform()
                self.assertTrue(bounds.contains(self.pet.geometry()))
                self.assertGreater(self.pet.width(), original.width())
                self.pet.start_idle()
                self.assertEqual(self.pet.geometry(), original)
        self.pet.set_scale_percent(100)
        self.pet.start_transform()
        self.pet.set_scale_percent(200)
        self.assertFalse(self.pet._transforming)
        self.assertEqual(self.pet.size(), QSize(360, 320))
        self.pet._stop_transform()
        self.assertEqual(self.pet.size(), QSize(360, 320))
