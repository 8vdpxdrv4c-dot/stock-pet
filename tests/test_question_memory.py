import copy
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from llm_client import LLMClient
from question_memory import QuestionMemory, compact_history, summarize_memory


class QuestionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "profile" / "memory.sqlite3"
        self.memory = QuestionMemory(self.path)

    def tearDown(self):
        self.folder.cleanup()

    def client(self, answer="模拟的完整回复", memory=None):
        client = LLMClient("fake", "https://invalid.example", "test", "猫咪角色",
                           question_memory=memory if memory is not None else self.memory)
        client.knowledge = Mock()
        client.knowledge.build.return_value = "知识库正文"
        create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=answer), finish_reason="stop")]))
        client._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return client, create

    def test_restart_recalls_questions_without_saving_answers(self):
        answer = "这是以前的完整回复，不应长期保存。"
        client, _ = self.client(answer)
        client.chat("怎么培养阅读习惯？")
        restored = QuestionMemory(self.path)
        restarted, create = self.client(memory=restored)
        restarted.chat("我以前问过哪些阅读习惯的问题？")
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("怎么培养阅读习惯？", prompt)
        self.assertIn("知识库正文", prompt)
        self.assertNotIn(answer, prompt)
        with closing(sqlite3.connect(self.path)) as db:
            columns = [row[1] for row in db.execute("PRAGMA table_info(questions)")]
            self.assertNotIn("answer", columns)
            self.assertNotIn(answer, " ".join(str(row) for row in db.execute("SELECT * FROM questions")))

    def test_duplicates_are_counted_once_and_unrelated_topics_are_not_injected(self):
        self.memory.remember("如何培养阅读习惯？")
        self.memory.remember("  如何培养阅读习惯？  ")
        rows = QuestionMemory(self.path).recall("阅读习惯怎么养成")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["asked_count"], 2)
        self.assertEqual(self.memory.build("桌宠的前腿为什么透明？"), "")
        self.assertEqual(self.memory.build("你好"), "")

    def test_general_recall_and_followup_remember_old_questions_after_restart(self):
        self.memory.remember("怎么判断公司的估值？")
        self.memory.remember("如何培养阅读习惯？")
        self.memory.remember("继续")
        context = QuestionMemory(self.path).build("我之前问过哪些问题？")
        self.assertIn("怎么判断公司的估值？", context)
        self.assertIn("如何培养阅读习惯？", context)
        followup = QuestionMemory(self.path).build("继续")
        self.assertIn("如何培养阅读习惯？", followup)
        self.assertNotIn("：继续", followup)

    def test_memory_budget_is_bounded_and_recent_questions_are_not_duplicated(self):
        for i in range(12):
            self.memory.remember(f"阅读习惯第{i}个问题？" + "希望进行详细阅读指导。" * 200)
        context = self.memory.build("阅读习惯怎么养成？")
        self.assertLessEqual(len(context), 2000)
        self.assertLessEqual(context.count("曾输入"), 5)
        self.memory.remember("跑步怎么训练？")
        self.assertEqual(self.memory.build("跑步训练", [{"role": "user", "content": "跑步怎么训练？"}]), "")

    def test_current_question_is_recorded_once_even_if_the_api_fails(self):
        client, create = self.client()
        create.side_effect = RuntimeError("timeout")
        with self.assertLogs("llm_client", level="ERROR"):
            client.chat("怎么培养阅读习惯？")
        rows = self.memory.recall("阅读习惯")
        self.assertEqual(rows[0]["asked_count"], 1)
        self.assertNotIn("历史问题记忆", create.call_args.kwargs["messages"][0]["content"])

    def test_read_only_profile_does_not_break_the_chat(self):
        client, _ = self.client()
        with patch("question_memory.sqlite3.connect", side_effect=sqlite3.OperationalError("read only")), \
             self.assertLogs("question_memory", level="ERROR"):
            self.assertEqual(client.chat("阅读习惯"), "模拟的完整回复")

    def test_only_two_compacted_turns_are_sent_and_source_history_is_preserved(self):
        history = []
        for i in range(8):
            history.extend([{"role": "user", "content": f"第{i}个问题"},
                            {"role": "assistant", "content": f"第{i}条回复开头" + "长回复。" * 1000 + f"第{i}条回复结尾"}])
        original = copy.deepcopy(history)
        compact = compact_history(history)
        self.assertEqual(len(compact), 4)
        self.assertLessEqual(sum(len(item["content"]) for item in compact), 4000)
        self.assertIn("第6条回复开头", compact[1]["content"])
        self.assertIn("第7条回复结尾", compact[-1]["content"])
        self.assertEqual(history, original)
        client, create = self.client()
        client.chat("新的问题", history)
        messages = create.call_args.kwargs["messages"]
        self.assertEqual(messages[1:-1], compact)

    def test_continuation_requests_do_not_become_long_term_questions(self):
        client, create = self.client()
        create.side_effect = [SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content="阅读"), finish_reason="length")]),
            SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content="建议。"), finish_reason="stop")])]
        self.assertEqual(client.chat("怎么培养阅读习惯？"), "阅读建议。")
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT content, asked_count FROM questions").fetchall(),
                             [("怎么培养阅读习惯？", 1)])

    def test_long_input_keeps_middle_values_after_restart_and_removes_repetition(self):
        message = ("以下是虚构练习记录。" + "背景：今天整理笔记。" * 60
                   + "关键记录：识别码为雪桥486，复盘时间为21:17。"
                   + "补充：继续整理其他素材。" * 60)
        self.memory.remember(message)
        restored = QuestionMemory(self.path)
        row = restored.recall("练习记录的识别码和复盘时间")[0]
        self.assertEqual(row["content"], message)
        self.assertLess(len(row["summary"]), len(message) // 4)
        self.assertIn("雪桥486", row["summary"])
        context = restored.build("练习记录的识别码和复盘时间")
        self.assertIn("雪桥486", context)
        self.assertIn("21:17", context)
        self.assertIn("虚构", context)
        self.assertLessEqual(context.count("背景：今天整理笔记。"), 1)

    def test_summary_preserves_corrections_negation_and_conditional_status(self):
        text = ("假设以后搬家，我的预算上限为8000元。"
                "更正：预算上限改为6000元，旧预算8000元作废。"
                "没有决定搬家，不要当成既定计划。" + "背景说明：整理思路。" * 100)
        summary = summarize_memory(text, 180)
        self.assertIn("假设", summary)
        self.assertIn("6000", summary)
        self.assertIn("8000元作废", summary)
        self.assertIn("没有决定搬家", summary)
        self.assertLessEqual(len(summary), 180)

    def test_unbroken_long_input_keeps_middle_identifier(self):
        text = "假设记录中的配置内容是" + "普通背景" * 200 + "关键识别码为雪桥486" + "补充背景" * 200
        summary = summarize_memory(text, 250, "记录的识别码")
        self.assertIn("雪桥486", summary)
        self.assertIn("假设", summary)
        self.assertLessEqual(len(summary), 250)

    def test_query_can_recover_detail_omitted_from_stored_summary(self):
        text = "我的项目记录如下。" + "".join(
            f"关键配置{index}：测试代号为ALPHA{index}。" for index in range(30))
        text += "我最喜欢的颜色是湖蓝色，因为这种颜色看起来清爽，我想以后用来布置自己的书桌。"
        self.memory.remember(text)
        with closing(sqlite3.connect(self.path)) as db:
            summary = db.execute("SELECT summary FROM questions").fetchone()[0]
        self.assertNotIn("湖蓝色", summary)
        context = QuestionMemory(self.path).build("我的项目记录中最喜欢的颜色是什么")
        self.assertIn("湖蓝色", context)
        self.assertLessEqual(len(context), 2000)

    def test_long_recent_user_turn_keeps_middle_values(self):
        message = "背景说明：随手整理素材。" * 60 + "关键记录：识别码为雪桥486。" + "补充说明：尚未做其他决定。" * 60
        history = [{"role": "user", "content": message}, {"role": "assistant", "content": "收到。"}]
        compact = compact_history(history)
        self.assertIn("雪桥486", compact[0]["content"])
        self.assertLessEqual(len(compact[0]["content"]), 500)
        self.assertEqual(history[0]["content"], message)

    def test_compacted_recent_input_is_not_duplicated_as_long_term_memory(self):
        message = "背景说明：整理素材。" * 80 + "关键记录：项目识别码为雪桥486。"
        self.memory.remember(message)
        history = compact_history([{"role": "user", "content": message}])
        self.assertEqual(self.memory.build("项目识别码", history), "")

    def test_existing_memory_database_is_upgraded_without_losing_questions(self):
        self.path.parent.mkdir(parents=True)
        message = "我的项目代号为雪桥486。"
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("""CREATE TABLE questions (
                id INTEGER PRIMARY KEY, normalized TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL, asked_count INTEGER NOT NULL DEFAULT 1,
                first_asked TEXT NOT NULL, last_asked TEXT NOT NULL)""")
            db.execute("INSERT INTO questions VALUES (?, ?, ?, ?, ?, ?)",
                       (1, message, message, 2, "old", "old"))
            db.execute("""CREATE TABLE question_terms (
                question_id INTEGER NOT NULL, term TEXT NOT NULL,
                PRIMARY KEY (question_id, term))""")
            db.executemany("INSERT INTO question_terms VALUES (?, ?)",
                           [(1, word) for word in self.memory._terms(message)])
            db.commit()
        rows = self.memory.recall("项目代号")
        self.assertEqual(rows[0]["asked_count"], 2)
        self.assertEqual(rows[0]["content"], message)
        self.assertIn("雪桥486", rows[0]["summary"])
        self.memory.remember(message)
        self.assertEqual(self.memory.recall("项目代号")[0]["asked_count"], 3)

    def test_broad_recall_questions_find_declarations_after_restart(self):
        self.memory.remember("我今天参加了项目讨论，项目代号是雪桥486。")
        for question in ("你还记得我什么？", "你记住了哪些信息？", "昨天我说了什么？", "我昨天做了什么？"):
            with self.subTest(question=question):
                context = QuestionMemory(self.path).build(question)
                self.assertIn("雪桥486", context)
                self.assertIn("保存于", context)

    def test_old_records_are_recalled_with_timestamps_and_memory_capability(self):
        self.memory.remember("我的项目代号是雪桥486。")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE questions SET first_asked = ?, last_asked = ?", (yesterday, yesterday))
            db.commit()
        restarted, create = self.client(memory=QuestionMemory(self.path))
        restarted.chat("我昨天说的项目代号是什么？")
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("雪桥486", prompt)
        self.assertIn("可跨天", prompt)
        self.assertIn(datetime.fromisoformat(yesterday).astimezone().strftime("%Y-%m-%d"), prompt)

    def test_no_matching_memory_still_explains_enabled_capability(self):
        client, create = self.client()
        client.chat("你能跨天自动记住我告诉你的内容吗？")
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("应用记忆能力", prompt)
        self.assertIn("可跨天", prompt)
        self.assertIn("本轮输入保存成功", prompt)
        self.assertNotIn("历史问题记忆", prompt)

    def test_read_and_save_failure_are_disclosed_without_claiming_saved_memory(self):
        client, create = self.client()
        with patch("question_memory.sqlite3.connect", side_effect=sqlite3.OperationalError("read only")), \
             self.assertLogs("question_memory", level="ERROR"):
            client.chat("请记住项目代号雪桥486。")
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("历史读取失败", prompt)
        self.assertIn("输入保存失败", prompt)
        self.assertNotIn("输入保存成功", prompt)
        self.assertFalse(self.memory.last_read_ok)
        self.memory.recall("项目代号")
        self.assertTrue(self.memory.last_read_ok)


if __name__ == "__main__":
    unittest.main()
