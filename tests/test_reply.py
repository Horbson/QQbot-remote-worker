# -*- coding: utf-8 -*-
import unittest

from utils.reply import BotReply, ReplyType, normalize_reply


class TestBotReply(unittest.TestCase):
    def test_string_reply_defaults_to_markdown(self):
        reply = normalize_reply("hello")

        self.assertEqual(reply.msg_type, ReplyType.MARKDOWN)
        self.assertEqual(reply.to_message_kwargs(), {
            "msg_type": 2,
            "markdown": {"content": "hello"},
        })

    def test_plaintext_reply(self):
        reply = BotReply.plaintext("hello")

        self.assertEqual(reply.to_message_kwargs(), {
            "msg_type": 0,
            "content": "hello",
        })

    def test_markdown_payload_mapping_reply(self):
        reply = normalize_reply({
            "msg_type": 2,
            "payload": {"content": "# title"},
        })

        self.assertEqual(reply.to_message_kwargs(), {
            "msg_type": 2,
            "markdown": {"content": "# title"},
        })

    def test_file_payload_mapping_reply(self):
        reply = normalize_reply({
            "msg_type": ReplyType.FILE,
            "payload": {
                "file_type": 1,
                "url": "https://example.com/image.png",
            },
        })

        self.assertEqual(reply.msg_type, ReplyType.FILE)
        self.assertEqual(reply.file_type, 1)
        self.assertEqual(reply.file_url, "https://example.com/image.png")


if __name__ == "__main__":
    unittest.main(verbosity=2)
