import os
import subprocess
from pathlib import Path

from botpy import logging

from mode.base import BaseMode
from utils.error_handler import SystemError, UserFriendlyError, handle_error

from . import messages_template as tpl

_log = logging.get_logger(__name__)


class CommandExecutionError(UserFriendlyError):
    """Command execution error."""
    pass


class CommandTimeoutError(UserFriendlyError):
    """Command timeout error."""
    pass


def run_command(command: str, cwd: str = ".", timeout: int = 5):
    """Run a system command and capture stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "output": result.stdout,
            "error": result.stderr,
        }
    except subprocess.TimeoutExpired as e:
        _log.warning(f"Command timeout after {timeout}s: {command}")
        raise CommandTimeoutError(f"命令执行超时（{timeout} 秒）") from e
    except FileNotFoundError as e:
        _log.warning(f"Command not found: {command}")
        cmd_name = command.split()[0] if command.split() else command
        raise CommandExecutionError(f"命令不存在：{cmd_name}") from e
    except PermissionError as e:
        _log.error(f"Command permission denied: {command}")
        raise CommandExecutionError("权限不足，无法执行该命令") from e
    except Exception as e:
        _log.exception(f"Command execution failed: {command}")
        raise SystemError("命令执行失败") from e


class Executor(BaseMode):
    """执行系统命令的模式。"""

    def __init__(self):
        self.cwd = "."

    def message_handler(self, message):
        command = message.content if hasattr(message, "content") else message
        try:
            result = run_command(command, timeout=10, cwd=self.cwd)

            if result["returncode"] != 0:
                _log.warning(f"Command returned non-zero code: {result['returncode']}")

            return tpl.COMMAND_SUCCESS.format(
                command=command,
                returncode=result["returncode"],
                output=result["output"],
                error=result["error"],
            )
        except (CommandTimeoutError, CommandExecutionError) as e:
            result = handle_error(e, "命令执行")
            return result["message"]
        except Exception as e:
            result = handle_error(e, "命令执行", "命令执行失败，请检查命令是否正确。")
            return result["message"]

    def set_cwd(self, target_cwd):
        _path = Path(target_cwd)
        if _path.is_dir():
            self.cwd = target_cwd
            return tpl.SET_CWD_SUCCESS
        return tpl.SET_CWD_NOT_FOUND

    def whereami(self, arg=None):
        if self.cwd == ".":
            return tpl.WHEREAMI_CURRENT.format(cwd=os.getcwd())
        return tpl.WHEREAMI_CURRENT.format(cwd=self.cwd)

    def command_handler(self, message, command=None, arg_str=None):
        if not hasattr(message, "content"):
            command, arg_str = message, command

        if command == "set_cwd":
            if arg_str:
                return self.set_cwd(arg_str)
            return tpl.SET_CWD_MISSING_ARG
        if command == "whereami":
            return self.whereami()
        return tpl.UNKNOWN_COMMAND.format(command=command, arg=arg_str)

    def helper(self, arg=None):
        return tpl.HELP_TEXT


if __name__ == "__main__":
    commands = [
        "echo Hi",
        "ping www.baidu.com -n 5",
        "python",
        "dir",
        "gugugaga",
        "powershell",
        "python -c \"import wrong_module\"",
    ]
    for cmd in commands:
        print(f"Running command: {cmd}")
        command_result = run_command(cmd, timeout=5)
        print(f"Return code: {command_result['returncode']}")
        print(f"Output:\n{command_result['output']}")
        print(f"Error:\n{command_result['error']}")
        print("\n", "-" * 40)
