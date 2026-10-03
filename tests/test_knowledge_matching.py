import json
import tempfile
import unittest
from pathlib import Path

from knowledge_context import KnowledgeContext
from knowledge_terms import field_list


class KnowledgeMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.context = KnowledgeContext(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def note(self, name, text):
        (self.root / name).write_text(text, encoding="utf-8")

    def selected(self, query, history=None):
        return [e.path for e in self.context.select(self.context.read_entries(), query, history)]

    def test_keywords_are_short_readable_arrays_without_body_noise(self):
        self.note("incentive.md", "---\ntags: [激励机制, 行为分析, 组织管理, 利益驱动]\n"
                  "keywords: [利益冲突, 2026-04-15, v1, a2, 95]\n"
                  "description: 理解激励机制与利益冲突。\n---\n# 激励机制分析\n"
                  "历史案例涉及代码审查、application、A1、2026-04-15 和 95。")
        entries = self.context.read_entries()
        record = json.loads((self.root / "registry.json").read_text(encoding="utf-8"))["entries"]["incentive.md"]
        self.assertIsInstance(record["keywords"], list)
        self.assertLessEqual(len(record["keywords"]), 16)
        self.assertEqual(len(record["keywords"]), 5)  # Good metadata needs no filler words.
        self.assertEqual(record["keywords"][0], "利益冲突")
        self.assertIn("激励机制", record["keywords"])
        self.assertFalse(set(record["keywords"]) & {"励机", "激励机", "2026-04-15", "v1", "a2", "95", "application", "代码审查"})
        self.assertEqual(self.selected("为什么激励机制会导致利益冲突"), ["incentive.md"])
        self.assertEqual(self.selected("励机"), [])
        self.assertEqual(self.selected("2026-04-15 v1 A2"), [])

    def test_generic_words_do_not_select_unrelated_material(self):
        self.note("incentive.md", "---\ntags: [激励机制]\ndescription: 设计管理制度与激励机制。\n---\n# 激励机制分析")
        self.note("trading.md", "---\ndescription: 设计交易策略，捕捉市场恐慌。\n---\n# 逆向交易")
        self.assertEqual(self.selected("激励机制怎么设计"), ["incentive.md"])
        self.assertEqual(self.selected("一个问题需要怎么设计处理"), [])

    def test_negative_scope_and_single_incidental_summary_word_do_not_match(self):
        self.note("note.md", "---\nkeywords: [激励机制]\n"
                  "description: 适用于组织制度分析。不适用于技术故障排查或数据库修复。\n---\n# 激励机制")
        self.assertEqual(self.selected("数据库故障如何修复"), [])
        self.assertEqual(self.selected("摄影作品怎么备份"), [])

    def test_explicit_phrases_english_boundaries_and_live_edit(self):
        self.note("note.md", "---\nkeywords:\n  - valuation\n  - 止损纪律\n"
                  "triggers:\n  - 舍不得割肉\n---\n# 我的笔记")
        self.assertEqual(self.selected("evaluation"), [])
        self.assertEqual(self.selected("need valuation"), ["note.md"])
        self.assertEqual(self.selected("现在舍不得割肉"), ["note.md"])
        self.note("note.md", "---\nkeywords: [摄影备份]\n---\n# 我的笔记")
        self.assertEqual(self.selected("need valuation"), [])
        self.assertEqual(self.selected("摄影备份"), ["note.md"])
        self.assertEqual(field_list('keywords: ["risk, return", 机会成本]', "keywords"), ["risk, return", "机会成本"])

    def test_history_only_extends_followups_not_new_topics_or_dates(self):
        self.note("risk.md", "# 止损纪律\n严格执行止损")
        history = [{"role": "user", "content": "止损怎么做"}]
        self.assertEqual(self.selected("那该怎么办", history), ["risk.md"])
        self.assertEqual(self.selected("今天吃什么", history), [])
        self.assertEqual(self.selected("2026-04-15", history), [])

    def test_chinese_phrases_do_not_match_inside_a_different_word(self):
        self.note("emotion.md", "---\nkeywords: [数据]\n---\n# 情绪即数据")
        self.note("database.md", "---\nkeywords: [数据库连接]\n---\n# 数据库连接排查")
        self.assertEqual(self.selected("数据库连接失败怎么排查"), ["database.md"])
        self.assertEqual(self.selected("情绪数据怎么理解"), ["emotion.md"])

    def test_support_words_alone_cannot_admit_a_document(self):
        self.note("trading.md", "---\nkeywords: [失败, 风险, 情绪]\n---\n# 交易中的失败与成本")
        self.assertEqual(self.selected("软件安装失败怎么排查"), [])
        self.assertEqual(self.selected("交易失败怎么办"), ["trading.md"])

    def test_scenarios_match_rephrasing_without_pooling_unrelated_fragments(self):
        self.note("incentive.md", "---\nkeywords: [激励机制]\ntriggers:\n"
                  "  - 员工追求考核指标，不顾客户体验\n"
                  "  - 销售忽略售后服务\n---\n# 激励机制")
        self.assertEqual(self.selected("员工只顾指标，却不在乎客户体验"), ["incentive.md"])
        self.assertEqual(self.selected("客户体验怎么提升"), [])
        self.assertEqual(self.selected("员工销售怎么培训"), [])
