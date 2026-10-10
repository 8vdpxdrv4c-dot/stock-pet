"""Declare and validate runtime data shared by every packaging mode."""
import json
from pathlib import Path

CAT_FILES = ("drag-play-actions-v2.png", "edge-peek-v2.png", "edge-peek-actions-v1.png",
             "transform-walk-sheet.png", "eye-reference.png", "eating-idle-v3-sheet.png")
CAT_FOLDERS = ("sitting-idle", "eating-idle", "eating-video-v7", "sleep-idle", "playing-idle",
               "walking-idle", "recycle-walking-video")


def collect_resources(root, config_folder):
    root, config_folder = Path(root), Path(config_folder)
    resources = []
    for name in CAT_FILES:
        file = root / "assets/cat" / name
        if not file.is_file():
            raise RuntimeError(f"缺少动画素材：{file}")
        resources.append((str(file), "assets/cat"))
    for name in CAT_FOLDERS:
        folder = root / "assets/cat" / name
        frames = sorted(folder.glob("*.png"))
        if not frames:
            raise RuntimeError(f"缺少动画帧：{folder}")
        for file in frames + sorted(folder.glob("*.json")):
            resources.append((str(file), f"assets/cat/{name}"))
    knowledge = root / "knowledge"
    if not any(knowledge.rglob("SKILL.md")):
        raise RuntimeError(f"缺少知识库：{knowledge}")
    for file in sorted(knowledge.rglob("*.md")):
        resources.append((str(file), str(file.parent.relative_to(root))))
    if (knowledge / "registry.json").is_file():
        resources.append((str(knowledge / "registry.json"), "knowledge"))
    config = json.loads((root / "config.json").read_text(encoding="utf-8-sig"))
    config["deepseek_api_key"] = ""
    for key in ("_system_prompt_template", "check_interval_minutes", "discipline"):
        config.pop(key, None)
    config_folder.mkdir(parents=True, exist_ok=True)
    bundled = config_folder / "config.json"
    bundled.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    resources.append((str(bundled), "."))
    return resources
