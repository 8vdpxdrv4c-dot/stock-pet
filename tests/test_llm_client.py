import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from llm_client import LLMClient


def completion(content, reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content), finish_reason=reason)])


class LLMReplyTests(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient("fake", "https://invalid.example", "test", "原角色")
        self.client.knowledge = Mock()
        self.client.knowledge.build.return_value = "相关知识正文"
        self.create = Mock()
        self.client._client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=self.create)))

    def test_complete_long_answer_is_not_cut_or_requested_again(self):
        answer = "完整的长回复。" * 300 + "回答结束。"
        self.create.return_value = completion(answer)
        self.assertEqual(self.client.chat("详细解释"), answer)
        self.create.assert_called_once()
        self.assertGreaterEqual(self.create.call_args.kwargs["max_tokens"], 4096)
        self.assertIn("相关知识正文", self.create.call_args.kwargs["messages"][0]["content"])

    def test_length_limit_continues_a_split_sentence_and_preserves_history(self):
        self.create.side_effect = [completion("第一点：应先确定", "length"),
                                   completion("规则。\n第二点：执行。", "length"),
                                   completion("\n回答结束。")]
        history = [{"role": "user", "content": "之前的问题"},
                   {"role": "assistant", "content": "之前的回复"}]
        original = copy.deepcopy(history)
        self.assertEqual(self.client.chat("详细解释", history),
                         "第一点：应先确定规则。\n第二点：执行。\n回答结束。")
        self.assertEqual(history, original)
        self.assertEqual(self.create.call_count, 3)
        first = self.create.call_args_list[0].kwargs["messages"]
        second = self.create.call_args_list[1].kwargs["messages"]
        self.assertEqual(first[-1], {"role": "user", "content": "详细解释"})
        self.assertEqual(second[-2], {"role": "assistant", "content": "第一点：应先确定"})
        self.assertIn("中断处", second[-1]["content"])
        self.assertEqual(second[0], first[0])
        self.client.knowledge.build.assert_called_once_with("详细解释", history)

    def test_repeated_truncation_is_bounded_and_explicit(self):
        self.create.return_value = completion("一段内容。", "length")
        reply = self.client.chat("特别长的回答")
        self.assertEqual(self.create.call_count, 3)
        self.assertTrue(reply.startswith("一段内容。" * 3))
        self.assertIn("回复仍未结束", reply)

    def test_continuation_failure_keeps_the_existing_answer(self):
        self.create.side_effect = [completion("已经收到的正文。", "length"), RuntimeError("timeout")]
        with self.assertLogs("llm_client", level="ERROR"):
            reply = self.client.chat("详细解释")
        self.assertTrue(reply.startswith("已经收到的正文。"))
        self.assertIn("续写暂时失败", reply)

    def test_empty_length_response_does_not_loop(self):
        self.create.return_value = completion(None, "length")
        self.assertIn("没有收到回复", self.client.chat("测试"))
        self.create.assert_called_once()

    def test_empty_continuation_is_not_reported_as_a_complete_answer(self):
        self.create.side_effect = [completion("尚未完成的内容。", "length"), completion(None)]
        reply = self.client.chat("详细解释")
        self.assertTrue(reply.startswith("尚未完成的内容。"))
        self.assertIn("续写没有返回内容", reply)


if __name__ == "__main__":
    unittest.main()
