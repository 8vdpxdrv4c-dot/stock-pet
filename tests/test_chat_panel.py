import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt, QThread, QPoint
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from chat_panel import ChatPanel, MessageBubble


class FakeClient:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def chat(self, message, history):
        self.calls.append((message, list(history)))
        QThread.msleep(60)
        if self.fail:
            raise RuntimeError("连接测试失败")
        return "<b>这是一条纯文本回复</b>\n第二行也要显示。"


class ChatPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for font in ("msyh.ttc", "msyhbd.ttc"):
            path = Path("C:/Windows/Fonts") / font
            if path.exists():
                QFontDatabase.addApplicationFont(str(path))

    def setUp(self):
        self.client = FakeClient()
        self.panel = ChatPanel(self.client, "花花")
        self.panel.show()
        QTest.qWait(20)

    def tearDown(self):
        if self.panel._worker:
            self.panel._worker.wait(2000)
        self.app.processEvents()
        self.panel.close()

    def wait_reply(self):
        for _ in range(100):
            QTest.qWait(10)
            if not self.panel._busy:
                return
        self.fail("Reply did not finish")

    def test_enter_sends_and_renders_safe_bubbles_with_history(self):
        self.panel.input.setText("你好 <script>")
        QTest.keyClick(self.panel.input, Qt.Key_Return)
        self.assertFalse(self.panel._send_btn.isEnabled())
        self.wait_reply()
        self.assertEqual(self.client.calls, [("你好 <script>", [])])
        self.assertEqual(self.panel.history[0], {"role": "user", "content": "你好 <script>"})
        self.assertTrue(self.panel._send_btn.isEnabled())
        reply = self.panel.findChildren(MessageBubble)[-1]
        self.assertEqual(reply.label.textFormat(), Qt.PlainText)
        self.assertIn("<b>", reply.label.text())
        self.panel.input.setText("继续")
        QTest.mouseClick(self.panel._send_btn, Qt.LeftButton)
        self.wait_reply()
        self.assertEqual(len(self.client.calls[1][1]), 2)

    def test_topics_send_once_preserve_draft_and_disable_while_waiting(self):
        self.panel.input.setText("还没写完的草稿")
        QTest.mouseClick(self.panel.quick_buttons[3], Qt.LeftButton)
        self.assertEqual(self.panel.input.text(), "还没写完的草稿")
        self.assertTrue(all(not button.isEnabled() for button in self.panel.quick_buttons))
        QTest.keyClick(self.panel.input, Qt.Key_Return)
        self.wait_reply()
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(self.client.calls[0][0], "讲个笑话喵")
        self.assertTrue(all(button.isEnabled() for button in self.panel.quick_buttons))

    def test_failure_recovers_and_name_changes_update_header(self):
        self.client.fail = True
        self.panel.input.setText("测试")
        self.panel._send()
        self.wait_reply()
        self.assertIn("连接测试失败", self.panel.messages[-1][1])
        self.assertTrue(self.panel._send_btn.isEnabled())
        self.panel.set_pet_name("小橘")
        self.assertEqual(self.panel.title_label.text(), "小橘")
        self.assertIn("小橘", self.panel.input.placeholderText())
        self.assertIn("小橘", self.panel.quick_buttons[0].text())

    def test_long_messages_wrap_and_scroll_without_covering_composer(self):
        self.panel._append_message("很长的消息需要正确换行。" * 60, "assistant")
        self.panel._append_message("连续文字" * 50, "user")
        QTest.qWait(80)
        bar = self.panel.browser.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        self.assertEqual(bar.value(), bar.maximum())
        self.assertEqual(self.panel.browser.horizontalScrollBar().maximum(), 0)
        for bubble in self.panel.findChildren(MessageBubble):
            x = bubble.mapTo(self.panel.browser.viewport(), QPoint()).x()
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x + bubble.width(), self.panel.browser.viewport().width())
        self.assertTrue(self.panel.input.isVisible())

    def test_only_last_two_turns_are_sent_as_temporary_history(self):
        for i in range(8):
            self.panel.history.extend([{"role": "user", "content": f"第{i}个问题"},
                                       {"role": "assistant", "content": f"第{i}个回复"}])
        expected = list(self.panel.history[-4:])
        self.panel.input.setText("新问题")
        self.panel._send()
        self.wait_reply()
        self.assertEqual(self.client.calls[0][1], expected)
