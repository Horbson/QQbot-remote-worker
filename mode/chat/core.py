import json

from mode.base import BaseMode
from utils.error_handler import handle_error

from . import messages_template as tpl
from .llm_tools import call_llm
from .prompts import build_system_prompt
from .tools import (
    TOOL_SCHEMAS,
    PendingOperation,
    dumps_tool_result,
    execute_tool,
    new_confirmation_id,
)


REASONING_LEVELS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


class Chat(BaseMode):
    def __init__(self):
        self.reasoning_effort = "medium"
        self.pending_operation = None
        self.max_tool_rounds = 5
        self.clear_context()

    def message_handler(self, message):
        if self.pending_operation is not None:
            return tpl.PENDING_CONFIRMATION_EXISTS.format(
                confirmation_id=self.pending_operation.confirmation_id,
                tool_name=self.pending_operation.tool_name,
                reason=self.pending_operation.reason,
            )

        content = message.content if hasattr(message, "content") else message
        self.context.append({"role": "user", "content": content})
        return self._run_agent_loop()

    def command_handler(self, message, command=None, arg_str=None):
        if not hasattr(message, "content"):
            command, arg_str = message, command

        if command == "new_session":
            self.clear_context()
            self.pending_operation = None
            return tpl.NEW_SESSION_SUCCESS
        if command == "reasoning":
            return self.set_reasoning_effort(arg_str)
        if command == "confirm":
            return self.confirm_pending_operation(arg_str)
        if command == "cancel":
            return self.cancel_pending_operation(arg_str)
        return tpl.UNKNOWN_COMMAND.format(command=command)

    def clear_context(self):
        self.context = [{"role": "system", "content": build_system_prompt()}]

    def set_reasoning_effort(self, level):
        if level not in REASONING_LEVELS:
            return tpl.REASONING_UNKNOWN_ARG.format(
                levels=", ".join(sorted(REASONING_LEVELS))
            )
        self.reasoning_effort = level
        return tpl.REASONING_SET_SUCCESS.format(level=level)

    def confirm_pending_operation(self, confirmation_id):
        if self.pending_operation is None:
            return tpl.NO_PENDING_CONFIRMATION
        if confirmation_id != self.pending_operation.confirmation_id:
            return tpl.CONFIRMATION_ID_MISMATCH.format(confirmation_id=confirmation_id)

        pending = self.pending_operation
        self.pending_operation = None
        tool_result = execute_tool(
            pending.tool_name,
            pending.arguments,
            confirmed=True,
        )
        self._append_tool_result(pending.tool_call_id, pending.tool_name, tool_result)
        return self._run_agent_loop()

    def cancel_pending_operation(self, confirmation_id):
        if self.pending_operation is None:
            return tpl.NO_PENDING_CONFIRMATION
        if confirmation_id != self.pending_operation.confirmation_id:
            return tpl.CONFIRMATION_ID_MISMATCH.format(confirmation_id=confirmation_id)

        pending = self.pending_operation
        self.pending_operation = None
        self._append_tool_result(
            pending.tool_call_id,
            pending.tool_name,
            {
                "success": False,
                "data": None,
                "error": "用户取消了该工具调用",
                "cancelled": True,
            },
        )
        return tpl.CONFIRMATION_CANCELLED.format(confirmation_id=confirmation_id)

    def helper(self, command=None):
        return tpl.HELP_TEXT

    def _run_agent_loop(self):
        try:
            for _ in range(self.max_tool_rounds):
                result = call_llm(
                    context=self.context,
                    reasoning_effort=self.reasoning_effort,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                    parallel_tool_calls=False,
                )
                self.context.append(result["message"])

                tool_calls = result.get("tool_calls") or []
                if not tool_calls:
                    content = result.get("content") or ""
                    return content or tpl.EMPTY_RESPONSE

                for tool_call in tool_calls:
                    confirmation_message = self._handle_tool_call(tool_call)
                    if confirmation_message is not None:
                        return confirmation_message

            return tpl.TOOL_LOOP_LIMIT
        except Exception as e:
            result = handle_error(e, "Chat agent")
            return result["message"]

    def _handle_tool_call(self, tool_call):
        function = tool_call.get("function", {})
        tool_name = function.get("name")
        arguments_text = function.get("arguments") or "{}"
        try:
            arguments = json.loads(arguments_text)
        except json.JSONDecodeError as e:
            tool_result = {
                "success": False,
                "data": None,
                "error": f"工具参数不是有效 JSON：{e}",
            }
            self._append_tool_result(tool_call.get("id"), tool_name, tool_result)
            return None

        tool_result = execute_tool(tool_name, arguments)
        if tool_result.get("needs_confirmation"):
            confirmation_id = new_confirmation_id()
            reason = tool_result.get("confirmation_reason") or tool_result.get("error") or "该操作需要确认"
            self.pending_operation = PendingOperation(
                confirmation_id=confirmation_id,
                tool_call_id=tool_call.get("id"),
                tool_name=tool_name,
                arguments=arguments,
                reason=reason,
            )
            return tpl.CONFIRMATION_REQUIRED.format(
                confirmation_id=confirmation_id,
                tool_name=tool_name,
                reason=reason,
            )

        self._append_tool_result(tool_call.get("id"), tool_name, tool_result)
        return None

    def _append_tool_result(self, tool_call_id, tool_name, tool_result):
        self.context.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": dumps_tool_result(tool_result),
        })
