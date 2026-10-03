import json
import os
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import parse_qs

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
import mindback_record as record


class MindbackTests(unittest.TestCase):
    def test_utf8_payload_and_ack(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"success":true,"data":{"acceptCode":"ACK","lastAckClientSeq":54}}'
        with patch.object(record.keyring, "get_password", return_value="test-session"), patch.object(record.urllib.request, "urlopen", return_value=response) as post:
            self.assertEqual(record.send_record("中午吃什么呢？", 54), 54)
        request = post.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(json.loads(payload["message"])["text"], "中午吃什么呢？")
        self.assertEqual(payload["chatId"], 2650536)
        self.assertEqual(payload["clientSeq"], 54)
        self.assertEqual(parse_qs(request.get_header("Xy-common-params"))["sid"], ["test-session"])

    def test_http_success_is_not_business_success(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"success":false,"msg":"login expired"}'
        with patch.object(record.keyring, "get_password", return_value="test-session"), patch.object(record.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "login expired"):
                record.send_record("记录", 54)

    def test_failure_preserves_input_and_success_clears_it(self):
        app = QApplication.instance() or QApplication([])
        dialog = record.RecordDialog(None)
        dialog.store = MagicMock()
        dialog.store.value.return_value = 53
        dialog.input.setPlainText("我的记录")
        sent_messages = []
        dialog.sent.connect(sent_messages.append)
        dialog.show()
        with patch.object(record, "send_record", side_effect=ValueError("登录失效")):
            dialog.send()
            for _ in range(100):
                QTest.qWait(10)
                if dialog.send_button.isEnabled():
                    break
        self.assertEqual(dialog.input.toPlainText(), "我的记录")
        self.assertIn("登录失效", dialog.status.text())
        self.assertTrue(dialog.isVisible())
        self.assertEqual(sent_messages, [])
        with patch.object(record, "send_record", return_value=54):
            dialog.send()
            for _ in range(100):
                QTest.qWait(10)
                if dialog.send_button.isEnabled():
                    break
        self.assertEqual(dialog.input.toPlainText(), "")
        self.assertIn("已发送", dialog.status.text())
        self.assertFalse(dialog.isVisible())
        self.assertEqual(len(sent_messages), 1)
        self.assertIn("发送成功", sent_messages[0])
        dialog.close()
