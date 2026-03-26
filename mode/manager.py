from utils.data import get_item

class ModeManager:
    def __init__(self, mode: dict, logger=None):
        self.modes_instances = [mode['class']() for mode in mode.values()]
        self.modes_descriptions = {name: mode[name]['description'] for name in mode}
        self.current_mode_index = 0
        self.modes_instances_count = len(self.modes_instances)

    def _get_mode_instance(self, target):
        if type(target) == str:
            target = list(self.modes_descriptions).index(target)
        return self.modes_instances[target]

    def message_handler(self, message):
        content = self.modes_instances[self.current_mode_index].message_handler(message)
        return content

    def get_current_mode_name(self, arg=None):
        return list(self.modes_descriptions.keys())[self.current_mode_index]

    def switch_mode(self, next_mode_name = None):
        if next_mode_name is None:
            self.current_mode_index = (self.current_mode_index + 1) % self.modes_instances_count
        else:
            modes_name = list(self.modes_descriptions.keys())
            if next_mode_name not in modes_name:
                return f"Mode {next_mode_name} not found. "
            else:
                self.current_mode_index = modes_name.index(next_mode_name)

        return f"Switched to {self.get_current_mode_name()} mode."

    def handle_command(self, command, arg):
        basic_command_map = {
            "switch": self.switch_mode,
            "help": self.get_some_help,
            "active_mode": self.get_current_mode_name,
            "modes": self.all_modes
        }
        if command in basic_command_map:
            return basic_command_map[command](arg)

        if ":" not in command:
            return f"未知命令: {command}."
        mode_name, command_name = command.split(":", 1)
        
        inst = self._get_mode_instance(mode_name)
        if inst is None:
            return f"未知命令: 没有{mode_name}模式."
        
        return inst.command_handler(command_name, arg)

    def get_some_help(self, mode_name: str=None):
        if mode_name is None:
            help_text = (
                "# 基本信息\n"
                "机器人会将非`/`开头的消息交给当前激活的模式处理。\n\n"
                "`/`开头的消息会被当做命令来处理。"
                "# 可用的基本命令：\n"
                " - /help: 显示帮助信息。使用/help <mode>可以查看特定模式的帮助信息。\n"
                " - /switch <mode>: 切换到指定模式。如果未指定模式，则根据顺序切换到下一个模式。\n"
                " - /active_mode: 显示当前激活的模式。\n"
                " - /modes: 列出所有可用的模式。\n"
                " - /<mode>:<command> <args>: 执行指定模式的子命令。"
            )
            return help_text
        else:
            inst = self._get_mode_instance(mode_name)
            if inst == None:
                return f"未知模式: 没有{mode_name}模式."
            else:
                return inst.helper()
            
    def all_modes(self, arg=None):
        message = "# 可用的模式: \n"
        for mode_name, description in self.modes_descriptions.items():
            message += f" - {mode_name}: {description}\n"
        return message
