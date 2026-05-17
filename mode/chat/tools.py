# -*- coding: utf-8 -*-
import json
import os
import platform
import re
import secrets
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_OUTPUT_CHARS = 12000
DEFAULT_MAX_READ_CHARS = 12000
DEFAULT_MAX_ENTRIES = 200


@dataclass(frozen=True)
class RiskDecision:
    needs_confirmation: bool
    reason: str = ""


@dataclass(frozen=True)
class PendingOperation:
    confirmation_id: str
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    reason: str


def new_confirmation_id() -> str:
    return secrets.token_hex(4)


def dumps_tool_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False)


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    max_chars = max(0, min(int(max_chars), 60000))
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n...[truncated]", True


def _success(data: Any = None, **extra) -> dict[str, Any]:
    result = {"success": True, "data": data, "error": None}
    result.update(extra)
    return result


def _failure(error: str, **extra) -> dict[str, Any]:
    result = {"success": False, "data": None, "error": error}
    result.update(extra)
    return result


def resolve_path(path: str | None = ".") -> tuple[Path, bool]:
    raw_path = Path(path or ".").expanduser()
    is_absolute = raw_path.is_absolute()
    if not is_absolute:
        raw_path = PROJECT_ROOT / raw_path
    return raw_path.resolve(strict=False), is_absolute


def is_inside_project(path: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(PROJECT_ROOT)
        return True
    except ValueError:
        return False


def classify_command_risk(cmd: str, shell: bool = True) -> RiskDecision:
    command = re.sub(r"\s+", " ", (cmd or "").strip())
    normalized = command.lower()
    if not normalized:
        return RiskDecision(False)

    if not shell:
        try:
            parts = shlex.split(command, posix=False)
        except ValueError:
            parts = command.split()
        exe = Path(parts[0]).name.lower() if parts else ""
        args = " ".join(part.lower() for part in parts[1:])
        if exe in {"rm", "del", "erase", "rmdir", "rd", "remove-item"}:
            return RiskDecision(True, f"命令 {exe} 会删除文件或目录")
        if exe in {"format", "diskpart", "mkfs", "fdisk", "dd", "shutdown", "reboot", "logoff"}:
            return RiskDecision(True, f"命令 {exe} 可能影响系统或磁盘")
        if exe in {"taskkill", "stop-process"}:
            return RiskDecision(True, f"命令 {exe} 会终止进程")
        if exe == "git" and re.search(r"\b(reset\s+--hard|clean|checkout\s+-f|restore\s+\.)\b", args):
            return RiskDecision(True, "该 git 命令可能丢弃未提交更改")
        if exe in {"reg", "bcdedit", "sc", "net"}:
            joined = f"{exe} {args}"
            if re.search(r"\b(reg\s+(delete|import)|bcdedit|sc\s+delete|net\s+stop)\b", joined):
                return RiskDecision(True, "该命令会修改系统配置或服务状态")
        return RiskDecision(False)

    dangerous_patterns = [
        (r"\b(remove-item|rm|del|erase|rmdir|rd)\b", "命令包含删除文件或目录的操作"),
        (r"\b(format|diskpart|mkfs|fdisk|dd)\b", "命令可能影响磁盘或分区"),
        (r"\bcipher\s+/w\b", "命令会擦除磁盘空闲空间"),
        (r"\b(shutdown|reboot|restart-computer|stop-computer|logoff)\b", "命令会关机、重启或注销"),
        (r"\b(taskkill|stop-process)\b", "命令会终止进程"),
        (r"\b(sc\s+delete|net\s+stop)\b", "命令会删除或停止系统服务"),
        (r"\b(reg\s+(delete|import)|bcdedit)\b", "命令会修改注册表或启动配置"),
        (r"\bgit\s+reset\s+--hard\b", "git reset --hard 会丢弃未提交更改"),
        (r"\bgit\s+clean\b", "git clean 会删除未跟踪文件"),
        (r"\bgit\s+checkout\s+-f\b", "git checkout -f 会强制覆盖工作区"),
        (r"\bgit\s+restore\s+\.\b", "git restore . 会丢弃工作区更改"),
        (r"(?:>|>>)\s*(?:[a-z]:\\|\\\\|/)", "命令将输出重定向到绝对路径"),
    ]
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return RiskDecision(True, reason)
    return RiskDecision(False)


def tool_pwd() -> dict[str, Any]:
    return _success({
        "project_root": str(PROJECT_ROOT),
        "cwd": os.getcwd(),
        "platform": platform.platform(),
    })


def tool_ls(path: str = ".", recursive: bool = False, max_entries: int = DEFAULT_MAX_ENTRIES) -> dict[str, Any]:
    resolved, _ = resolve_path(path)
    if not resolved.exists():
        return _failure("路径不存在", resolved_path=str(resolved))
    if not resolved.is_dir():
        return _failure("目标不是目录", resolved_path=str(resolved))

    max_entries = max(1, min(int(max_entries), 1000))
    iterator = resolved.rglob("*") if recursive else resolved.iterdir()
    entries = []
    truncated = False
    try:
        for item in iterator:
            if len(entries) >= max_entries:
                truncated = True
                break
            try:
                stat = item.stat()
                size = stat.st_size if item.is_file() else None
            except OSError:
                size = None
            entries.append({
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
                "size": size,
            })
    except OSError as e:
        return _failure(str(e), resolved_path=str(resolved))

    return _success(entries, resolved_path=str(resolved), truncated=truncated)


def tool_read(path: str, max_chars: int = DEFAULT_MAX_READ_CHARS, encoding: str = "utf-8") -> dict[str, Any]:
    resolved, _ = resolve_path(path)
    if not resolved.exists():
        return _failure("文件不存在", resolved_path=str(resolved))
    if not resolved.is_file():
        return _failure("目标不是文件", resolved_path=str(resolved))

    try:
        content = resolved.read_text(encoding=encoding)
    except UnicodeDecodeError as e:
        return _failure(f"无法使用编码 {encoding} 解码文件：{e}", resolved_path=str(resolved))
    except OSError as e:
        return _failure(str(e), resolved_path=str(resolved))

    content, truncated = _truncate(content, max_chars)
    return _success(
        {"content": content},
        resolved_path=str(resolved),
        truncated=truncated,
        encoding=encoding,
    )


def _write_needs_confirmation(path: str, resolved: Path, mode: str) -> RiskDecision:
    _, is_absolute = resolve_path(path)
    if is_absolute:
        return RiskDecision(True, "写入绝对路径需要确认")
    if not is_inside_project(resolved):
        return RiskDecision(True, "写入项目目录外路径需要确认")
    if resolved.exists() and mode in {"overwrite", "append"}:
        return RiskDecision(True, "修改已有文件需要确认")
    return RiskDecision(False)


def tool_write(
    path: str,
    content: str,
    mode: str = "create",
    encoding: str = "utf-8",
    create_dirs: bool = False,
    confirmed: bool = False,
) -> dict[str, Any]:
    if mode not in {"create", "overwrite", "append"}:
        return _failure("mode 只能是 create、overwrite 或 append")

    resolved, _ = resolve_path(path)
    decision = _write_needs_confirmation(path, resolved, mode)
    if decision.needs_confirmation and not confirmed:
        return _failure(
            decision.reason,
            resolved_path=str(resolved),
            needs_confirmation=True,
            confirmation_reason=decision.reason,
        )

    if mode == "create" and resolved.exists():
        return _failure("文件已存在，若要覆盖请使用 overwrite 模式", resolved_path=str(resolved))
    if not resolved.parent.exists():
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        else:
            return _failure("父目录不存在", resolved_path=str(resolved))
    if resolved.exists() and not resolved.is_file():
        return _failure("目标不是文件", resolved_path=str(resolved))

    try:
        if mode == "append":
            with resolved.open("a", encoding=encoding) as f:
                f.write(content)
        else:
            with resolved.open("w", encoding=encoding) as f:
                f.write(content)
    except OSError as e:
        return _failure(str(e), resolved_path=str(resolved))

    return _success(
        {"bytes_written": len(content.encode(encoding))},
        resolved_path=str(resolved),
        truncated=False,
        encoding=encoding,
    )


def tool_exec(
    cmd: str,
    shell: bool = True,
    timeout: int = 10,
    cwd: str | None = None,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    confirmed: bool = False,
) -> dict[str, Any]:
    decision = classify_command_risk(cmd, shell=shell)
    if decision.needs_confirmation and not confirmed:
        return _failure(
            decision.reason,
            needs_confirmation=True,
            confirmation_reason=decision.reason,
        )

    timeout = max(1, min(int(timeout), 120))
    max_output_chars = max(0, min(int(max_output_chars), 60000))
    resolved_cwd, _ = resolve_path(cwd or ".")
    if not resolved_cwd.exists() or not resolved_cwd.is_dir():
        return _failure("工作目录不存在或不是目录", resolved_path=str(resolved_cwd))

    try:
        command: str | list[str]
        command = cmd
        if not shell:
            command = shlex.split(cmd, posix=os.name != "nt")
        result = subprocess.run(
            command,
            shell=shell,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            cwd=str(resolved_cwd),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _failure(f"命令执行超时（{timeout} 秒）", resolved_path=str(resolved_cwd))
    except Exception as e:
        return _failure(str(e), resolved_path=str(resolved_cwd))

    stdout, stdout_truncated = _truncate(result.stdout or "", max_output_chars)
    stderr, stderr_truncated = _truncate(result.stderr or "", max_output_chars)
    return _success(
        {
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
        },
        resolved_path=str(resolved_cwd),
        truncated=stdout_truncated or stderr_truncated,
    )


def execute_tool(tool_name: str, arguments: dict[str, Any], confirmed: bool = False) -> dict[str, Any]:
    try:
        if tool_name == "pwd":
            return tool_pwd()
        if tool_name == "ls":
            return tool_ls(**arguments)
        if tool_name == "read":
            return tool_read(**arguments)
        if tool_name == "write":
            return tool_write(**arguments, confirmed=confirmed)
        if tool_name == "exec":
            return tool_exec(**arguments, confirmed=confirmed)
        return _failure(f"未知工具：{tool_name}")
    except TypeError as e:
        return _failure(f"工具参数错误：{e}")


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "执行 shell 命令。危险命令会进入确认流程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string"},
                    "shell": {"type": "boolean", "default": True},
                    "timeout": {"type": "integer", "default": 10, "minimum": 1, "maximum": 120},
                    "cwd": {"type": "string", "description": "工作目录。省略时使用项目根目录。"},
                    "max_output_chars": {"type": "integer", "default": DEFAULT_MAX_OUTPUT_CHARS},
                },
                "required": ["cmd"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ls",
            "description": "列出目录内容。相对路径按项目根目录解析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "recursive": {"type": "boolean", "default": False},
                    "max_entries": {"type": "integer", "default": DEFAULT_MAX_ENTRIES},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "读取文本文件内容。相对路径按项目根目录解析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "default": DEFAULT_MAX_READ_CHARS},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "写入文本文件。项目外路径、绝对路径和修改已有文件会进入确认流程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "mode": {"type": "string", "enum": ["create", "overwrite", "append"], "default": "create"},
                    "encoding": {"type": "string", "default": "utf-8"},
                    "create_dirs": {"type": "boolean", "default": False},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pwd",
            "description": "返回项目根目录、当前工作目录和平台信息。",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]
