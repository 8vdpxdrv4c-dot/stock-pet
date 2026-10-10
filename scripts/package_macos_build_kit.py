"""Export only application sources and required assets, with no user credentials."""
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packaging_resources import collect_resources

SOURCES = (
    "action_icons.py", "app_paths.py", "build_distribution.py", "build_macos.py",
    "chat_panel.py", "config.py", "credential_store.py", "eye_texture.py",
    "idle_interaction.py", "keyboard_input.py", "knowledge_context.py", "knowledge_terms.py",
    "llm_client.py", "main.py", "mindback_record.py", "packaging_check.py",
    "packaging_resources.py", "pet_actions.py", "pet_widget.py", "question_memory.py",
    "reminder_manager.py", "settings_dialog.py", "speech_bubble.py", "startup.py",
    "todo_dialog.py", "StockPet-macOS.spec", "requirements.txt", "README.md",
    "build-mac.command", "packaging/runtime_log.py", "docs/macOS安装说明.txt",
    ".github/workflows/build-macos.yml", "tests/test_macos_compatibility.py",
    "tests/test_settings_dialog.py", "tests/test_packaging.py",
)
INSTRUCTIONS = """StockPet macOS 构建包

这是源码和完整运行素材的构建包，尚不是可直接安装的 Mac 成品。

在 Mac 上构建：
1. 安装 Python 3.11 / 3.12：https://www.python.org/downloads/macos/
2. 解压本 ZIP。
3. 在终端输入 bash 和一个空格，将 build-mac.command 拖到终端，按回车。
4. 等待依赖安装、打包及成品自检；成功后自动打开 dist/macos。
5. 选择符合 Mac 芯片的 DMG，打开并将 StockPet.app 拖入 Applications。

arm64 对应 Apple 芯片，x86_64 对应 Intel。使用的 Python 架构决定生成的架构。
无需复制 Windows 的 exe；所有动画、知识库和 Python 源码已包含。
本包不包含 API Key、对话历史、待办和凭据文件。
打包成品的签名及安装方式见 docs/macOS安装说明.txt。

GitHub 云端构建：
将构建包内容提交到仓库的 codex/macos-* 分支，GitHub Actions 自动生成两种架构。
在该次 Build macOS 运行的 Artifacts 下载安装包。
"""


def main():
    output = ROOT / "dist/StockPet-macOS-build-kit.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        resources = collect_resources(ROOT, temporary)
        files = {name: ROOT / name for name in SOURCES}
        for source, destination in resources:
            name = (Path(destination) / Path(source).name).as_posix()
            files[name] = Path(source)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            bundle.writestr("StockPet-macOS/先读我.txt", INSTRUCTIONS)
            for name, source in sorted(files.items()):
                info = zipfile.ZipInfo("StockPet-macOS/" + name)
                info.create_system = 3
                mode = 0o100755 if name.endswith(".command") else 0o100644
                info.external_attr = mode << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, source.read_bytes())
    with zipfile.ZipFile(output) as bundle:
        bad = bundle.testzip()
        if bad:
            raise RuntimeError(f"ZIP 校验失败：{bad}")
        print(f"构建包：{output}\n文件数：{len(bundle.namelist())}")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    print(f"大小：{output.stat().st_size / 1024 / 1024:.1f} MB\nSHA256：{digest}")


if __name__ == "__main__":
    main()
