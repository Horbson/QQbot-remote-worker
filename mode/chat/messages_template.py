# -*- coding: utf-8 -*-
"""
Chat 模式消息模板配置
所有用户可见的回复消息都应从这里获取模板
"""

# new_session 命令回复
NEW_SESSION_SUCCESS = "已清除上下文，开始新的会话。"

# reasoning 命令回复
REASONING_SET_SUCCESS = "已将推理强度设置为：{level}"
REASONING_UNKNOWN_ARG = "未知推理强度。可用等级：{levels}"

# 工具确认回复
CONFIRMATION_REQUIRED = """操作需要确认。
- 工具：{tool_name}
- 原因：{reason}
- 确认：/chat:confirm {confirmation_id}
- 取消：/chat:cancel {confirmation_id}
"""
PENDING_CONFIRMATION_EXISTS = """当前有待确认操作尚未处理。
- 工具：{tool_name}
- 原因：{reason}
- 确认：/chat:confirm {confirmation_id}
- 取消：/chat:cancel {confirmation_id}
"""
NO_PENDING_CONFIRMATION = "当前没有待确认操作。"
CONFIRMATION_ID_MISMATCH = "确认编号不匹配：{confirmation_id}"
CONFIRMATION_CANCELLED = "已取消待确认操作：{confirmation_id}"
TOOL_LOOP_LIMIT = "工具调用次数过多，已停止本轮处理。"
EMPTY_RESPONSE = "模型没有返回可发送的内容。"

# 未知命令模板
UNKNOWN_COMMAND = "未知命令：Chat 模式没有{command}命令。"

# 帮助信息
HELP_TEXT = """# chat 模式帮助
chat 模式是一个可调用本地工具的轻量 agent。

## 可用命令
- `/chat:new_session`：清除上下文和待确认操作。
- `/chat:reasoning <none|minimal|low|medium|high|xhigh|max>`：设置推理强度。
- `/chat:confirm <id>`：确认一次待执行操作。
- `/chat:cancel <id>`：取消一次待确认操作。
"""
