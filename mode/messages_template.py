# -*- coding: utf-8 -*-
"""
Mode Manager 消息模板配置
所有用户可见的回复消息都应从这里获取模板
"""

# 模式切换回复
SWITCH_MODE_SUCCESS = "Switched to {mode_name} mode."
SWITCH_MODE_NOT_FOUND = "Mode {mode_name} not found. "

# 未知命令回复
UNKNOWN_COMMAND = "未知命令：{command}."
UNKNOWN_MODE_COMMAND = "未知命令：没有{mode_name}模式."

# 帮助信息模板
HELP_BASIC = """# 基本信息
机器人会将非`/`开头的消息交给当前激活的模式处理。

`/`开头的消息会被当做命令来处理。
# 可用的基本命令：
 - /help: 显示帮助信息。使用/help <mode>可以查看特定模式的帮助信息。
 - /switch <mode>: 切换到指定模式。如果未指定模式，则根据顺序切换到下一个模式。
 - /active_mode: 显示当前激活的模式。
 - /modes: 列出所有可用的模式。
 - /<mode>:<command> <args>: 执行指定模式的子命令。
"""

HELP_MODE_NOT_FOUND = "未知模式：没有{mode_name}模式."

# 模式列表回复
MODES_LIST_HEADER = "# 可用的模式：\n"
MODES_LIST_ITEM = " - {mode_name}: {description}\n"
