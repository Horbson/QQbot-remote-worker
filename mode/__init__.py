from .manager import ModeManager

from .executor import Executor
from .chat import Chat

modes = {
    "exec": {
        "class": Executor,
        "description": "执行系统命令的模式。"
    },
    "chat": {
        "class": Chat,
        "description": "普通聊天模式，适合日常对话和问答。"
    }
}

mode_manager = ModeManager(modes)