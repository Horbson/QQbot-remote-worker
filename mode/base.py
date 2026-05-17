class BaseMode:
    """
    模式类模板。所有模式类都应该继承自这个基类，并实现其中的方法。
    以下列出的方法必须被被重写。
    """
    def message_handler(self, message):
        """
        处理消息的接口，接受完整消息对象，返回回复内容字符串或 BotReply。
        """
        pass

    def command_handler(self, message, command, arg_str):
        """
        处理命令的接口，接受完整消息对象、子命令和参数字符串，返回回复内容字符串或 BotReply。
        如果子命令不存在，根据以下约定返回错误消息：
        """
        unknown_command_msg_template = "未知命令：{mode}模式没有{command}命令。"
        pass

    def helper(self, command=None):
        """
        返回帮助信息的接口，接受可选的子命令参数，返回帮助信息字符串。
        """
        pass

class ExampleMode(BaseMode):
    """
    示例模式，展示了一个简单的回声模式。
    在该模式下，机器人会复述消息内容。
    并可以通过执行/ExampleMode:set_prefix <prefix>命令来设置复述前缀。
    """
    def __init__(self):
        self.echo_prefix = "Echo: "

    def message_handler(self, message):
        """
        简单地返回收到的消息内容。
        """
        return f"Echo: {message.content}"
    
    def set_prefix(self, arg_str: str):
        """
        设置回声前缀的命令处理函数。
        """
        self.echo_prefix = arg_str.strip()
        return f"Echo prefix set to: {self.echo_prefix}"
    
    command_map = {
        "set_prefix": set_prefix
    }
    
