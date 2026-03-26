from .llm_tools import call_llm
from mode.base import BaseMode

class Chat(BaseMode):
    def __init__(self):
        self.clear_context()
        self.thinking = True
    
    def message_handler(self, message):
        self.context.append(
            {"role": "user", "content": message}
        )
        result = call_llm(context=self.context, thinking=self.thinking)
        return f"```\n思考: {result['reasoning_content']}\n```\n{result['content']}\n"

    def command_handler(self, command, arg_str):
        if command == "new_session":
            self.clear_context()
            return "已清除上下文，开始新的会话。"
        elif command == "thinking":
            if arg_str == "enable":
                self.thinking = True
                return "已启用思考过程展示。"
            elif arg_str == "disable":
                self.thinking = False
                return "已禁用思考过程展示。"
            else:
                return "未知参数: thinking命令只接受enable或disable作为参数。"
            
        else:
            return f"未知命令: Chat模式没有{command}命令。"

    def clear_context(self):
        with open("./mode/chat/prompts/IDENTITY.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        self.context = [
            {"role": "system", "content": system_prompt}
        ]
    
    def helper(self, command=None):
        help_context = [
            self.context[0],
            {"role": "user", "content": "我需要一些关于机器人Chat模式的帮助。"}
        ]

        result = call_llm(context=help_context, thinking=False)
        return result['content']