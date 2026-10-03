import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from llm_client import LLMClient
from knowledge_context import KnowledgeContext


class KnowledgeContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, slug, description, body):
        path = self.root / slug / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {slug}\ndescription: |\n  {description}\n---\n# {slug}\n{body}", encoding="utf-8")
        return path

    def test_every_request_includes_catalog_and_refreshes_relevant_body(self):
        path = self.write_skill("stop-loss", "止损执行不了、舍不得割肉", "初版止损正文")
        self.write_skill("valuation", "估值和现金流计算", "估值完整正文不该出现")
        client = LLMClient("fake", "https://invalid.example", "test", "角色设定", self.root)
        create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=" OK "))]))
        client._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        history = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}]
        original = copy.deepcopy(history)
        self.assertEqual(client.chat("舍不得止损", history), "OK")
        messages = create.call_args.kwargs["messages"]
        prompt = messages[0]["content"]
        self.assertTrue(prompt.startswith("角色设定"))
        self.assertIn("valuation/SKILL.md", prompt)
        self.assertIn("初版止损正文", prompt)
        self.assertNotIn("估值完整正文不该出现", prompt)
        self.assertEqual(messages[1:-1], history)
        self.assertEqual(history, original)
        self.assertEqual(client.system_prompt, "角色设定")
        path.write_text(path.read_text(encoding="utf-8").replace("初版", "新版"), encoding="utf-8")
        client.chat("舍不得止损")
        self.assertIn("新版止损正文", create.call_args.kwargs["messages"][0]["content"])
        path.unlink()
        client.chat("舍不得止损")
        self.assertNotIn("stop-loss/SKILL.md", create.call_args.kwargs["messages"][0]["content"])

    def test_history_selection_limits_and_non_skill_exclusions(self):
        self.write_skill("risk", "止损交易风险", "风险正文")
        self.write_skill("value", "现金流估值", "估值正文")
        self.write_skill("_blind/ignored", "止损", "排除盲测")
        self.write_skill("rejected/ignored", "止损", "排除废案")
        (self.root / "book.txt").write_text("不加载原书", encoding="utf-8")
        context = KnowledgeContext(self.root, max_items=1)
        skills = context.read_entries()
        self.assertEqual(len(skills), 2)
        selected = context.select(skills, "那该怎么办", [{"role": "user", "content": "我不肯止损"}])
        self.assertEqual([skill.path for skill in selected], ["risk/SKILL.md"])
        prompt = context.build("止损")
        self.assertNotIn("不加载原书", prompt)
        self.assertNotIn("排除盲测", prompt)
        context.max_body_chars = 1
        self.assertEqual(context.select(skills, "止损", []), [])

    def test_missing_empty_and_invalid_files(self):
        self.assertEqual(KnowledgeContext(self.root / "missing").build("test"), "")
        self.assertEqual(KnowledgeContext(self.root).build("test"), "")
        bad = self.root / "bad" / "SKILL.md"
        bad.parent.mkdir()
        bad.write_bytes(b"\xff\xfe\x00")
        with self.assertLogs("knowledge_context", level="WARNING"):
            self.assertEqual(KnowledgeContext(self.root).build("test"), "")
        (self.root / "SKILL.md").write_text("# 顶层技能\n止损方法", encoding="utf-8")
        with self.assertLogs("knowledge_context", level="WARNING"):
            self.assertIn("顶层技能", KnowledgeContext(self.root).build("止损"))
