import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from knowledge_context import KnowledgeContext, default_knowledge_dir
from llm_client import LLMClient


class KnowledgeContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.notes = self.base / "knowledge"
        self.notes.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, root, relative, content):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_single_directory_deduplicates_and_excludes_support_files(self):
        original = "---\nname: discipline\ndescription: 止损纪律\n---\n# 止损纪律\n先确定止损规则。"
        self.write(self.notes, "pack/discipline/SKILL.md", original)
        self.write(self.notes, "投资/复制.md", original + " \n")
        self.write(self.notes, "个人/我的规则.md", "# 我的规则\n每次出差结束都要备份摄影作品。")
        for name in ("README.md", "_templates/示例.md", "tests/测试.md", "BOOK_OVERVIEW.md", "DIGEST.md", "verified.md", "PIPELINE_STATE.md"):
            self.write(self.notes, name, "# 不加载\n不应当出现")
        self.write(self.notes, "停用.md", "---\nenabled: false\n---\n# 停用知识\n不应出现")
        self.write(self.notes, "book.txt", "不加载原书")
        context = KnowledgeContext(self.notes)
        entries = context.read_entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].path, "pack/discipline/SKILL.md")
        selected = context.select(entries, "摄影作品怎么处理", [])
        self.assertEqual(selected[0].path, "个人/我的规则.md")
        prompt = context.build("摄影作品怎么处理")
        self.assertIn("全部知识目录", prompt)
        self.assertIn("止损纪律", prompt)
        self.assertNotIn("不应", prompt)

    def test_note_metadata_updates_and_disable_reach_every_llm_request(self):
        note = self.write(self.notes, "生活/习惯.md",
                          "---\ntitle: 我的喝水习惯\nenabled: true\ntriggers: [喝水]\n"
                          "source: 个人记录\n---\n正文：原来用蓝杯子。")
        client = LLMClient("fake", "https://invalid.example", "test", "原角色",
                           self.notes)
        create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]))
        client._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        client.chat("喝水")
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("我的喝水习惯", prompt)
        self.assertIn("个人记录", prompt)
        self.assertIn("蓝杯子", prompt)
        note.write_text(note.read_text(encoding="utf-8").replace("蓝杯子", "白杯子"), encoding="utf-8")
        client.chat("喝水")
        self.assertIn("白杯子", create.call_args.kwargs["messages"][0]["content"])
        note.write_text(note.read_text(encoding="utf-8").replace("enabled: true", "enabled: false"), encoding="utf-8")
        client.chat("喝水")
        self.assertEqual(create.call_args.kwargs["messages"][0]["content"], "原角色")

    def test_legacy_can_be_disabled_without_moving_files(self):
        self.write(self.notes, "pack/SKILL.md", "---\nenabled: false\n---\n# 暂停")
        self.assertEqual(KnowledgeContext(self.notes).read_entries(), [])

    def test_installed_app_uses_editable_directory_when_present(self):
        bundle = self.base / "bundle"
        with patch("knowledge_context.sys.frozen", True, create=True), \
             patch("knowledge_context.sys.executable", str(self.base / "StockPet.exe")), \
             patch("knowledge_context.BASE_DIR", str(bundle)):
            self.assertEqual(default_knowledge_dir(), self.notes)
            self.notes.rmdir()
            self.assertEqual(default_knowledge_dir(), bundle / "knowledge")
