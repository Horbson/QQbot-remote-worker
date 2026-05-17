# -*- coding: utf-8 -*-
"""
Executor 模式消息模板配置
所有用户可见的回复消息都应从这里获取模板
"""

# 命令执行结果模板
COMMAND_SUCCESS = """# 命令执行完成
 - 命令内容：{command}
 - 返回码：{returncode}
 - 输出:
```
{output}
```
 - 错误:
```
{error}
```
"""

# 错误消息模板
COMMAND_TIMEOUT = "执行命令超时：{command}"
COMMAND_ERROR = "执行命令时发生错误：{error}"

# set_cwd 命令回复模板
SET_CWD_SUCCESS = "Success."
SET_CWD_NOT_FOUND = "目标路径不存在。"
SET_CWD_MISSING_ARG = "Missing argument."

# whereami 命令回复模板
WHEREAMI_CURRENT = "{cwd}"

# 未知命令模板
UNKNOWN_COMMAND = "这是 exec 模式的命令处理函数。收到命令：{command}, 参数：{arg}"

# 帮助信息模板
HELP_TEXT = """# exec 模式帮助
在 exec 模式下，发送的**每条**消息都会被当作命令执行。
> 注意：没有拦截和确认机制，请三思后再发送命令。同时注意不要把机器人权限暴露给别人。
## 可用命令
 - `/exec:set_cwd <path>`: 设置命令执行的工作目录，默认为当前目录。
 - `/exec:whereami` :查看当前工作目录。
"""
