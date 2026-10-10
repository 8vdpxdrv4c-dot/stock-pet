import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_distribution as builder
from packaging_resources import collect_resources


class PackagingTests(unittest.TestCase):
    def test_runtime_assets_are_complete_and_config_is_sanitized(self):
        root = Path(__file__).resolve().parents[1]
        before = (root / "config.json").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            resources = collect_resources(root, folder)
            names = {Path(source).name for source, _ in resources}
            for name in ("drag-play-actions-v2.png", "edge-peek-v2.png", "edge-peek-actions-v1.png", "animation.json"):
                self.assertIn(name, names)
            bundled = json.loads((Path(folder) / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(bundled["deepseek_api_key"], "")
            self.assertNotIn("discipline", bundled)
        self.assertEqual((root / "config.json").read_bytes(), before)

    def test_missing_animation_fails_before_building(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "缺少动画素材"):
                collect_resources(folder, Path(folder) / "output")

    def test_default_single_exe_build_does_not_need_inno_setup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = root / "dist/StockPet.exe"
            calls = []

            def build(command, log, env):
                calls.append((command, env["STOCKPET_BUILD_MODE"]))
                executable.parent.mkdir(parents=True)
                executable.write_bytes(b"MZ-test")

            with patch.object(builder, "ROOT", root), patch.object(builder, "find_python", return_value="python.exe"), \
                 patch("packaging_resources.collect_resources", return_value=[]), \
                 patch.object(builder, "find_compiler", side_effect=AssertionError("EXE should not need ISCC")), \
                 patch.object(builder, "run_logged", side_effect=build):
                self.assertEqual(builder.main([]), 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], "onefile")

    def test_installer_missing_compiler_fails_before_pyinstaller(self):
        with patch.object(builder, "find_python", return_value="python.exe"), \
             patch("packaging_resources.collect_resources", return_value=[]), \
             patch.object(builder, "find_compiler", return_value=None), patch.object(builder, "run_logged") as run:
            self.assertEqual(builder.main(["--installer"]), 1)
            run.assert_not_called()

    def test_failed_build_is_reported(self):
        with patch.object(builder, "find_python", return_value="python.exe"), \
             patch("packaging_resources.collect_resources", return_value=[]), \
             patch.object(builder, "run_logged", side_effect=RuntimeError("打包失败")):
            self.assertEqual(builder.main([]), 1)
