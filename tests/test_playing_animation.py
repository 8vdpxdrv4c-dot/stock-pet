import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from config import ASSETS_DIR
from pet_widget import PetWidget
from pet_actions import PetActions


class PlayingAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.pet = PetWidget()

    def tearDown(self):
        self.pet.close()

    def test_play_menu_routes_to_animation_and_disables_sitting_overlays(self):
        from main import App
        menu = PetActions(self.pet)
        try:
            menu.action_requested.connect(lambda action: App._on_pet_action(SimpleNamespace(pet=self.pet), action))
            self.pet.start_sleeping()
            self.pet._set_dock_edge("left")
            QTest.mouseClick(menu.buttons["play"], Qt.LeftButton)
            self.assertIs(self.pet._current_group(), self.pet._playing_frames)
            self.assertFalse(self.pet._idle_interaction.enabled())
            self.assertFalse(self.pet._sleeping)
            self.assertIsNone(self.pet._dock_edge)
            self.assertTrue(self.pet._frame_timer.isActive())
        finally:
            menu.close()

    def test_play_resumes_after_walk_drag_transform_and_state_restore(self):
        pet = self.pet
        pet.start_playing()
        pet._frame_idx = 12
        state = pet.animation_state()
        self.assertEqual(state["action"], "play")
        pet.start_eating()
        self.assertFalse(pet._playing)
        pet.restore_animation_state(state)
        self.assertEqual(pet._frame_idx, 12)
        pet.walk_to(pet.pos() + QPoint(20, 0))
        pet.stop_walk()
        pet._start_drag_animation()
        pet._stop_drag_animation()
        pet.start_transform()
        pet._stop_transform()
        self.assertIs(pet._current_group(), pet._playing_frames)
        self.assertEqual(pet._frame_timer.interval(), pet._playing_interval)
        for action in (pet.start_sleeping, pet.start_eating, pet.start_idle):
            pet.start_playing()
            action()
            self.assertFalse(pet._playing)

    def test_extracted_frames_load_with_transparent_padding_and_loop(self):
        folder = Path(ASSETS_DIR) / "cat/playing-idle"
        manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8"))
        pet = self.pet
        pet.start_playing()
        self.assertEqual(len(pet._playing_frames), manifest["frame_count"])
        self.assertGreater(len(pet._playing_frames), 48)
        self.assertEqual(len(pet._playing_frames), 2 * manifest["source_frame_count"] - 2)
        # The wrap is an ordinary adjacent source-frame step, with no dissolve.
        self.assertEqual(pet._playing_frames[-1].toImage(), pet._playing_frames[1].toImage())
        self.assertEqual(pet._frame_timer.interval(), manifest["timer_interval_ms"])
        for frame in pet._playing_frames:
            image = frame.toImage()
            self.assertEqual([image.width(), image.height()], manifest["canvas_size"])
            for x in range(image.width()):
                self.assertEqual(image.pixelColor(x, 0).alpha(), 0)
                self.assertEqual(image.pixelColor(x, image.height() - 1).alpha(), 0)
        self.assertNotEqual(pet._playing_frames[0].toImage(), pet._playing_frames[40].toImage())
        pet._frame_idx = len(pet._playing_frames) - 1
        pet._on_frame_tick()
        self.assertEqual(pet._frame_idx, 0)

    def test_ground_reflections_are_transparent_but_real_paws_remain(self):
        # Actual regression locations from the standing and raised-paw poses.
        # Coordinates are on the existing 360x360 canvas, not a recropped image.
        samples = {
            0: {"reflection": [(140, 346), (214, 335)],
                "paw": [(140, 331), (184, 333), (250, 325)]},
            135: {"reflection": [(127, 347), (190, 349)],
                  "paw": [(133, 333), (191, 337), (219, 333)]},
        }
        for index, points in samples.items():
            frame = self.pet._playing_frames[index].toImage()
            for x, y in points["reflection"]:
                with self.subTest(frame=index, reflection=(x, y)):
                    self.assertLessEqual(frame.pixelColor(x, y).alpha(), 2)
            for x, y in points["paw"]:
                with self.subTest(frame=index, paw=(x, y)):
                    self.assertGreaterEqual(frame.pixelColor(x, y).alpha(), 240)
