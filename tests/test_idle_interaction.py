import ctypes
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from keyboard_input import KeyboardInput, RAWINPUTHEADER, RAWKEYBOARD
from pet_widget import PetWidget


class IdleInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_mouse_directions_tap_repeat_and_action_gating(self):
        pet = PetWidget()
        try:
            pet.show()
            interaction = pet._idle_interaction
            center = pet.mapToGlobal(pet.rect().center())
            for offset, sign in ((QPoint(-400, -400), -1), (QPoint(400, 400), 1)):
                with patch("idle_interaction.QCursor.pos", return_value=center + offset):
                    interaction.tick()
                self.assertGreater(interaction.gaze.x() * sign, .5)
                self.assertGreater(interaction.gaze.y() * sign, .5)
            interaction.tap()
            self.assertTrue(interaction.tap_clock.isValid())
            QTest.qWait(40)
            self.assertGreater(interaction.paw_lift(), 0)
            interaction.tap()
            self.assertLess(interaction.tap_clock.elapsed(), 20)
            QTest.qWait(180)
            interaction.tick()
            self.assertFalse(interaction.tap_clock.isValid())
            for action in (pet.start_eating, pet.start_sleeping, pet.start_transform):
                action()
                interaction.tap()
                self.assertFalse(interaction.enabled())
                self.assertFalse(interaction.tap_clock.isValid())
            pet.start_idle()
            self.assertTrue(interaction.enabled())
            pet.hide()
            self.assertFalse(interaction.timer.isActive())
        finally:
            pet.close()

    def test_distant_cursor_in_same_quadrant_changes_rendered_eyes_at_small_size(self):
        pet = PetWidget(scale_percent=50)
        try:
            pet.show()
            center = pet.mapToGlobal(pet.rect().center())
            gazes, images = [], []
            for offset in (QPoint(-1200, -300), QPoint(-300, -1200)):
                with patch("idle_interaction.QCursor.pos", return_value=center + offset):
                    pet._idle_interaction.tick()
                gazes.append(QPointF(pet._idle_interaction.gaze))
                images.append(pet.grab().toImage())
            self.assertGreater(abs(gazes[0].x() - gazes[1].x()), .5)
            changed = [(x, y) for y in range(images[0].height())
                       for x in range(images[0].width())
                       if images[0].pixel(x, y) != images[1].pixel(x, y)]
            self.assertGreater(len(changed), 20)
            self.assertTrue(all(18 <= y <= 28 for x, y in changed))
        finally:
            pet.close()

    def test_raw_keyboard_only_emits_down_and_repeat(self):
        listener = KeyboardInput()
        presses = []
        listener.key_pressed.connect(lambda: presses.append(True))
        header = RAWINPUTHEADER()
        header.kind = 1
        header.size = ctypes.sizeof(header) + ctypes.sizeof(RAWKEYBOARD)
        keyboard = RAWKEYBOARD()

        def get_input(handle, command, buffer, size_ptr, header_size):
            size_ptr._obj.value = header.size
            if buffer is None:
                return 0
            ctypes.memmove(buffer, ctypes.byref(header), ctypes.sizeof(header))
            ctypes.memmove(ctypes.addressof(buffer) + header_size,
                           ctypes.byref(keyboard), ctypes.sizeof(keyboard))
            return header.size

        listener._user32 = SimpleNamespace(GetRawInputData=get_input)
        for flags in (0, 0, 1):
            keyboard.flags = flags
            listener._read_input(123)
        self.assertEqual(presses, [True, True])
        header.kind = 0  # Mouse records are ignored.
        listener._read_input(123)
        self.assertEqual(len(presses), 2)
