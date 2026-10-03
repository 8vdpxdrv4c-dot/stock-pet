import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QRegion
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from pet_actions import PetActions
from pet_widget import PetWidget


class PetActionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.pet = PetWidget(scale_percent=150)
        self.pet._idle_interaction.stop()
        self.pet._frame_timer.stop()
        self.pet.move(270, 260)
        self.pet.show()
        self.menu = PetActions(self.pet)
        self.app.processEvents()

    def tearDown(self):
        self.menu.close()
        self.pet.close()

    def cat_region(self):
        pixels = self.pet.grab().scaled(self.pet.size(), Qt.IgnoreAspectRatio, Qt.FastTransformation)
        return QRegion(pixels.mask()).translated(self.pet.pos())

    def test_icon_buttons_keep_each_action_and_descriptive_tooltips(self):
        requested = []
        self.menu.action_requested.connect(requested.append)
        for action, label in self.menu.ACTIONS:
            self.menu.toggle()
            button = self.menu.buttons[action]
            self.assertEqual(button.text(), "")
            self.assertFalse(button.icon().isNull())
            self.assertEqual(button.toolTip(), label)
            self.assertEqual(button.accessibleName(), label)
            QTest.mouseClick(button, Qt.LeftButton)
            self.assertFalse(self.menu.isVisible())
        self.assertEqual(requested, [action for action, _ in self.menu.ACTIONS])

    def test_popup_hit_region_leaves_cat_and_desktop_clear(self):
        self.menu.toggle()
        mask = self.menu.mask().translated(self.menu.pos())
        cat = self.cat_region()
        self.assertTrue(mask.intersected(cat).isEmpty())
        for button in self.menu.buttons.values():
            self.assertTrue(mask.contains(button.mapToGlobal(button.rect().center())))
            self.assertFalse(self.menu.mask().contains(button.geometry().topLeft()))
        self.menu.toggle()
        self.assertFalse(self.menu.isVisible())

    def test_arc_stays_visible_and_separated_at_screen_corners(self):
        bounds = QRect(-1920, 0, 1920, 1080)
        for scale in (50, 100, 150, 300):
            self.pet.set_scale_percent(scale)
            self.menu._style_buttons()
            for left in (bounds.left(), bounds.right() - self.pet.width() + 1):
                for top in (bounds.top(), bounds.bottom() - self.pet.height() + 1):
                    with self.subTest(scale=scale, left=left, top=top):
                        self.pet.move(left, top)
                        boxes = self.menu._arrange(bounds)
                        cat = self.cat_region()
                        self.assertEqual(len(boxes), 6)
                        for box in boxes:
                            self.assertTrue(bounds.contains(box))
                            self.assertTrue(QRegion(box, QRegion.Ellipse).intersected(cat).isEmpty())
                        for i, first in enumerate(boxes):
                            for second in boxes[i + 1:]:
                                self.assertTrue(QRegion(first, QRegion.Ellipse).intersected(
                                    QRegion(second, QRegion.Ellipse)).isEmpty())

    def test_escape_and_pet_movement_dismiss_popup(self):
        self.menu.toggle()
        QTest.keyClick(self.menu, Qt.Key_Escape)
        self.assertFalse(self.menu.isVisible())
        self.menu.toggle()
        self.pet.move(self.pet.x() + 10, self.pet.y())
        self.assertFalse(self.menu.isVisible())
