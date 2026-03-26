import subprocess
from pathlib import Path
from mode.base import BaseMode
import os

def run_command(command: str, cwd: str = ".", timeout: int = 5):
    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        stdin = subprocess.DEVNULL,
        cwd=cwd,
        timeout=timeout
    )

    return {
        "returncode": result.returncode,
        "output": result.stdout,
        "error": result.stderr
    }


class Executor(BaseMode):
    def __init__(self):
        self.cwd = "."

    def message_handler(self, message):
        try:
            result = run_command(message, timeout=10, cwd=self.cwd)
            return_content =  ("# 命令执行完成\n"
                     f" - 命令内容：{message}\n"
                     f" - 返回码: {result['returncode']}\n"
                     f" - 输出:\n```\n{result['output']}\n```\n"
                     f" - 错误:\n```\n{result['error']}\n```\n"
                     )
            return return_content
        except subprocess.TimeoutExpired:
            return f"执行命令超时: {message.content}"
        except Exception as e:
            return f"执行命令时发生错误: {str(e)}"

    def set_cwd(self, target_cwd):
        _path = Path(target_cwd)
        if _path.is_dir():
            self.cwd = target_cwd
            return "Success."
        else:
            return "目标路径不存在。"

    def whereami(self, arg=None):
        if self.cwd == ".":
            return os.getcwd()
        else:
            return self.cwd

    def command_handler(self, command, arg_str=None):
        if command == "set_cwd":
            if arg_str:
                self.set_cwd(arg_str)
                return "Success."
            else:
                return "Missing argument."
        elif command == "whereami":
            return self.whereami()
        return f"这是exec模式的命令处理函数. 收到命令: {command}, 参数: {arg_str}"

    def helper(self, arg=None):
        return (
            "# exec模式帮助\n"
            "在exec模式下，发送的**每条**消息都会被当作命令执行。\n"
            "> 注意：没有拦截和确认机制，请三思后再发送命令。同时注意不要把机器人权限暴露给别人。\n"
            "## 可用命令\n"
            " - `/exec:set_cwd <path>`: 设置命令执行的工作目录，默认为当前目录。\n"
            " - `/exec:whereami` :查看当前工作目录。"
        )

if __name__ == "__main__":
    # 测试
    commands = ["echo Hi", "ping www.baidu.com -n 5", "python", "dir", "gugugaga", "powershell", "python -c \"import wrong_module\""]
    for cmd in commands:
        print(f"Running command: {cmd}")
        result = run_command(cmd, timeout=5)
        print(f"Return code: {result['returncode']}")
        print(f"Output:\n{result['output']}")
        print(f"Error:\n{result['error']}")
        print("\n", "-" * 40)