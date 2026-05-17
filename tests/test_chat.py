# -*- coding: utf-8 -*-
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from mode.chat import messages_template as tpl
from mode.chat.core import Chat
from mode.chat.prompts import build_system_prompt
from mode.chat.tools import (
    PendingOperation,
    classify_command_risk,
    execute_tool,
)
from utils.error_handler import ConfigurationError


class TestChatClass(unittest.TestCase):
    def setUp(self):
        self.chat = Chat()

    def test_initialization(self):
        chat = Chat()
        self.assertIsInstance(chat.context, list)
        self.assertEqual(chat.reasoning_effort, "medium")
        self.assertIsNone(chat.pending_operation)

    def test_clear_context(self):
        self.chat.context.append({"role": "user", "content": "test"})
        self.chat.context.append({"role": "assistant", "content": "test"})

        self.chat.clear_context()

        self.assertEqual(len(self.chat.context), 1)
        self.assertEqual(self.chat.context[0]["role"], "system")
        self.assertIn("本地 agent", self.chat.context[0]["content"])

    def test_build_system_prompt(self):
        prompt = build_system_prompt()

        self.assertIsInstance(prompt, str)
        self.assertIn("write", prompt)
        self.assertIn("exec", prompt)

    def test_command_handler_new_session_clears_pending(self):
        self.chat.context.append({"role": "user", "content": "test"})
        self.chat.pending_operation = PendingOperation(
            confirmation_id="abc",
            tool_call_id="call_1",
            tool_name="exec",
            arguments={"cmd": "del x"},
            reason="danger",
        )

        result = self.chat.command_handler("new_session", None)

        self.assertEqual(result, tpl.NEW_SESSION_SUCCESS)
        self.assertEqual(len(self.chat.context), 1)
        self.assertIsNone(self.chat.pending_operation)

    def test_command_handler_reasoning(self):
        result = self.chat.command_handler("reasoning", "high")

        self.assertEqual(result, tpl.REASONING_SET_SUCCESS.format(level="high"))
        self.assertEqual(self.chat.reasoning_effort, "high")

    def test_command_handler_reasoning_max(self):
        result = self.chat.command_handler("reasoning", "max")

        self.assertIn("max", result)
        self.assertEqual(self.chat.reasoning_effort, "max")

    def test_command_handler_reasoning_unknown_arg(self):
        result = self.chat.command_handler("reasoning", "extreme")

        self.assertIn("未知推理强度", result)
        self.assertEqual(self.chat.reasoning_effort, "medium")

    def test_command_handler_thinking_removed(self):
        result = self.chat.command_handler("thinking", "enable")

        self.assertEqual(result, tpl.UNKNOWN_COMMAND.format(command="thinking"))

    def test_helper(self):
        result = self.chat.helper()

        self.assertIn("chat 模式帮助", result)


class TestChatAgentLoop(unittest.TestCase):
    def setUp(self):
        self.chat = Chat()

    @patch("mode.chat.core.call_llm")
    def test_message_handler_returns_final_answer_and_records_assistant(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": "这是回答",
            "tool_calls": [],
            "message": {"role": "assistant", "content": "这是回答"},
        }

        initial_length = len(self.chat.context)
        result = self.chat.message_handler("你好")

        self.assertEqual(result, "这是回答")
        self.assertEqual(len(self.chat.context), initial_length + 2)
        self.assertEqual(self.chat.context[-1]["role"], "assistant")
        mock_call_llm.assert_called_once()
        self.assertEqual(mock_call_llm.call_args.kwargs["reasoning_effort"], "medium")

    @patch("mode.chat.core.call_llm")
    def test_tool_call_result_is_appended_and_model_called_again(self, mock_call_llm):
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "pwd", "arguments": "{}"},
        }
        mock_call_llm.side_effect = [
            {
                "content": None,
                "tool_calls": [tool_call],
                "message": {"role": "assistant", "content": "", "tool_calls": [tool_call]},
            },
            {
                "content": "完成",
                "tool_calls": [],
                "message": {"role": "assistant", "content": "完成"},
            },
        ]

        result = self.chat.message_handler("看一下当前位置")

        self.assertEqual(result, "完成")
        self.assertEqual(mock_call_llm.call_count, 2)
        tool_messages = [item for item in self.chat.context if item["role"] == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0]["tool_call_id"], "call_1")
        self.assertIn("project_root", tool_messages[0]["content"])

    @patch("mode.chat.core.call_llm")
    def test_dangerous_tool_call_requests_confirmation(self, mock_call_llm):
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "exec",
                "arguments": json.dumps({"cmd": "del important.txt"}),
            },
        }
        mock_call_llm.return_value = {
            "content": None,
            "tool_calls": [tool_call],
            "message": {"role": "assistant", "content": "", "tool_calls": [tool_call]},
        }

        result = self.chat.message_handler("删除文件")

        self.assertIn("/chat:confirm", result)
        self.assertIsNotNone(self.chat.pending_operation)
        self.assertEqual(self.chat.pending_operation.tool_name, "exec")

    def test_message_handler_blocks_when_confirmation_pending(self):
        self.chat.pending_operation = PendingOperation(
            confirmation_id="abc",
            tool_call_id="call_1",
            tool_name="exec",
            arguments={"cmd": "del x"},
            reason="命令包含删除文件或目录的操作",
        )

        result = self.chat.message_handler("新的消息")

        self.assertIn("/chat:confirm abc", result)

    @patch("mode.chat.core.call_llm")
    def test_confirm_pending_operation_executes_and_continues(self, mock_call_llm):
        self.chat.pending_operation = PendingOperation(
            confirmation_id="abc",
            tool_call_id="call_1",
            tool_name="pwd",
            arguments={},
            reason="test",
        )
        mock_call_llm.return_value = {
            "content": "确认后已完成",
            "tool_calls": [],
            "message": {"role": "assistant", "content": "确认后已完成"},
        }

        result = self.chat.command_handler("confirm", "abc")

        self.assertEqual(result, "确认后已完成")
        self.assertIsNone(self.chat.pending_operation)
        self.assertEqual(self.chat.context[-2]["role"], "tool")

    def test_cancel_pending_operation_appends_cancelled_tool_result(self):
        self.chat.pending_operation = PendingOperation(
            confirmation_id="abc",
            tool_call_id="call_1",
            tool_name="exec",
            arguments={"cmd": "del x"},
            reason="danger",
        )

        result = self.chat.command_handler("cancel", "abc")

        self.assertIn("已取消", result)
        self.assertIsNone(self.chat.pending_operation)
        self.assertEqual(self.chat.context[-1]["role"], "tool")
        self.assertIn("用户取消", self.chat.context[-1]["content"])


class TestChatTools(unittest.TestCase):
    def test_ls_project_root(self):
        result = execute_tool("ls", {"path": ".", "max_entries": 200})

        self.assertTrue(result["success"])
        self.assertTrue(any(item["name"] == "README.md" for item in result["data"]))
        self.assertIn("resolved_path", result)

    def test_read_file(self):
        result = execute_tool("read", {"path": "README.md", "max_chars": 30})

        self.assertTrue(result["success"])
        self.assertIn("content", result["data"])
        self.assertTrue(result["truncated"])

    def test_write_create_project_file(self):
        path = Path(".tmp") / "agent_tool_test.txt"
        absolute = Path(__file__).parent.parent / path
        if absolute.exists():
            absolute.unlink()

        result = execute_tool(
            "write",
            {
                "path": str(path),
                "content": "hello",
                "mode": "create",
                "create_dirs": True,
            },
        )

        try:
            self.assertTrue(result["success"])
            self.assertTrue(absolute.exists())
            self.assertEqual(absolute.read_text(encoding="utf-8"), "hello")
        finally:
            if absolute.exists():
                absolute.unlink()

    def test_write_overwrite_needs_confirmation(self):
        result = execute_tool(
            "write",
            {
                "path": "README.md",
                "content": "new content",
                "mode": "overwrite",
            },
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["needs_confirmation"])

    def test_write_absolute_path_needs_confirmation(self):
        result = execute_tool(
            "write",
            {
                "path": str(Path(__file__).resolve()),
                "content": "new content",
                "mode": "overwrite",
            },
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["needs_confirmation"])

    def test_exec_safe_command(self):
        result = execute_tool("exec", {"cmd": "echo hi", "timeout": 5})

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["returncode"], 0)
        self.assertIn("hi", result["data"]["stdout"])

    def test_exec_dangerous_command_needs_confirmation(self):
        result = execute_tool("exec", {"cmd": "git reset --hard"})

        self.assertFalse(result["success"])
        self.assertTrue(result["needs_confirmation"])

    def test_classify_dangerous_commands(self):
        self.assertTrue(classify_command_risk("del important.txt", shell=True).needs_confirmation)
        self.assertTrue(classify_command_risk("git reset --hard", shell=True).needs_confirmation)
        self.assertFalse(classify_command_risk("echo safe", shell=True).needs_confirmation)


class TestChatMessagesTemplate(unittest.TestCase):
    def test_new_session_template(self):
        self.assertIsInstance(tpl.NEW_SESSION_SUCCESS, str)
        self.assertIn("清除", tpl.NEW_SESSION_SUCCESS)

    def test_reasoning_template(self):
        result = tpl.REASONING_SET_SUCCESS.format(level="high")
        self.assertIn("high", result)

    def test_unknown_command_template(self):
        result = tpl.UNKNOWN_COMMAND.format(command="test_cmd")
        self.assertIn("test_cmd", result)
        self.assertIn("未知命令", result)


class TestChatLLMCall(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_MODEL_ID": "test-model"}, clear=True)
    def test_resolve_model_id_from_env(self):
        from mode.chat.llm_tools.llm_call import resolve_model_id

        self.assertEqual(resolve_model_id(), "test-model")

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_model_id_missing_raises_configuration_error(self):
        from mode.chat.llm_tools.llm_call import resolve_model_id

        with self.assertRaises(ConfigurationError):
            resolve_model_id()

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_MODEL_ID": "test-model",
        },
        clear=True,
    )
    @patch("mode.chat.llm_tools.llm_call.load_dotenv")
    @patch("mode.chat.llm_tools.llm_call.OpenAI")
    def test_call_llm_uses_model_id_from_env(self, mock_openai, mock_load_dotenv):
        from mode.chat.llm_tools import call_llm

        message = type("Message", (), {"content": "ok", "tool_calls": None})()
        choice = type("Choice", (), {"message": message})()
        response = type("Response", (), {"choices": [choice]})()
        mock_openai.return_value.chat.completions.create.return_value = response

        result = call_llm(context=[{"role": "user", "content": "hi"}], reasoning_effort="none")

        self.assertEqual(result["content"], "ok")
        request_kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(request_kwargs["model"], "test-model")

    @unittest.skip("需要有效的 LLM API 配置")
    def test_call_llm_basic(self):
        from mode.chat.llm_tools import call_llm

        context = [
            {"role": "system", "content": "你是一个有用的助手"},
            {"role": "user", "content": "你好"},
        ]

        result = call_llm(context=context, reasoning_effort="none")

        self.assertIsInstance(result, dict)
        self.assertIn("content", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
