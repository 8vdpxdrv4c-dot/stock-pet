"""Offline smoke check for the actual frozen application and its resources."""
import json
import tempfile
from pathlib import Path


def run():
    from PyQt5.QtWidgets import QApplication
    from config import load_config
    from pet_widget import PetWidget
    from settings_dialog import SettingsDialog
    from todo_dialog import TodoDialog, ReminderTimeDialog
    from knowledge_context import KnowledgeContext
    from question_memory import QuestionMemory
    import keyring

    app = QApplication.instance() or QApplication([])
    pet = PetWidget()
    windows = [pet]
    try:
        counts = {name: len(frames) for name, frames in {
            "idle": pet._frames.get("idle", []), "eat": pet._eating_frames,
            "sleep": pet._sleep_frames, "play": pet._playing_frames, "walk": pet._walk_frames,
            "recycle_walk": pet._recycle_walk_frames, "drag": pet._drag_frames,
            "transform": pet._transform_frames, "peek": pet._peek_frames,
        }.items()}
        if pet._use_placeholder or not all(counts.values()) or pet._peek_sprite.isNull():
            raise RuntimeError(f"动画素材加载不完整：{counts}")
        original = pet.size()
        pet.start_transform()
        pet.grab()
        pet._stop_transform()
        if pet.size() != original:
            raise RuntimeError("变身结束未恢复尺寸")
        settings = SettingsDialog(load_config())
        windows.append(settings)
        with tempfile.TemporaryDirectory() as folder:
            todo = TodoDialog(storage_path=Path(folder) / "todos.json")
            todo.input.setText("打包自检")
            todo.add_task()
            picker = ReminderTimeDialog(todo.tasks[0], todo)
            windows.extend([todo, picker])
            memory = QuestionMemory(Path(folder) / "memory.sqlite3")
            if not memory.remember("打包检查代号：橘猫验证731"):
                raise RuntimeError("记忆库无法保存")
            if not QuestionMemory(Path(folder) / "memory.sqlite3").recall("橘猫验证731"):
                raise RuntimeError("记忆库无法重新读取")
        entries = KnowledgeContext().read_entries()
        if not entries:
            raise RuntimeError("知识库为空")
        print("PACKAGING_SMOKE_OK " + json.dumps({"frames": counts, "knowledge_entries": len(entries),
                                                 "keyring_backend": type(keyring.get_keyring()).__name__},
                                                ensure_ascii=False), flush=True)
        return 0
    finally:
        pet._idle_interaction.stop()
        for window in reversed(windows):
            window.close()
        app.processEvents()
