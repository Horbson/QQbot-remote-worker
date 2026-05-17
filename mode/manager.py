from botpy.message import C2CMessage

from utils.error_handler import ConfigurationError

from . import messages_template as tpl


class ModeManager:
    def __init__(self, mode: dict, logger=None):
        self.modes_instances = [config["class"]() for config in mode.values()]
        self.modes_descriptions = {
            name: config["description"] for name, config in mode.items()
        }
        self.current_mode_index = 0
        self.modes_instances_count = len(self.modes_instances)

    def _ensure_modes_available(self):
        if self.modes_instances_count == 0:
            raise ConfigurationError("没有可用的运行模式，请检查 mode 插件加载日志")

    def _get_mode_instance(self, target):
        self._ensure_modes_available()
        if isinstance(target, str):
            try:
                target = list(self.modes_descriptions).index(target)
            except ValueError:
                return None
        try:
            return self.modes_instances[target]
        except (IndexError, TypeError):
            return None

    def message_handler(self, message: C2CMessage):
        self._ensure_modes_available()
        content = self.modes_instances[self.current_mode_index].message_handler(message)
        return content

    def get_current_mode_name(self, arg=None):
        self._ensure_modes_available()
        return list(self.modes_descriptions.keys())[self.current_mode_index]

    def switch_mode(self, next_mode_name=None):
        self._ensure_modes_available()
        if next_mode_name is None:
            self.current_mode_index = (
                self.current_mode_index + 1
            ) % self.modes_instances_count
        else:
            modes_name = list(self.modes_descriptions.keys())
            if next_mode_name not in modes_name:
                return tpl.SWITCH_MODE_NOT_FOUND.format(mode_name=next_mode_name)
            self.current_mode_index = modes_name.index(next_mode_name)

        return tpl.SWITCH_MODE_SUCCESS.format(mode_name=self.get_current_mode_name())

    def handle_command(self, message: C2CMessage, arg=None):
        command, arg = self._parse_command(message, arg)
        basic_command_map = {
            "switch": self.switch_mode,
            "help": self.get_some_help,
            "active_mode": self.get_current_mode_name,
            "modes": self.all_modes,
        }
        if command in basic_command_map:
            return basic_command_map[command](arg)

        if ":" not in command:
            return tpl.UNKNOWN_COMMAND.format(command=command)
        mode_name, command_name = command.split(":", 1)

        inst = self._get_mode_instance(mode_name)
        if inst is None:
            return tpl.UNKNOWN_MODE_COMMAND.format(mode_name=mode_name)

        return inst.command_handler(message, command_name, arg)

    @staticmethod
    def _parse_command(message, arg=None):
        if hasattr(message, "content"):
            content = message.content or ""
            if content.startswith("/"):
                content = content[1:]
            proc_content = content.split(" ", 1)
            command = proc_content[0]
            arg = proc_content[1] if len(proc_content) > 1 else None
            return command, arg

        return message, arg

    def get_some_help(self, mode_name: str = None):
        if mode_name is None:
            return tpl.HELP_BASIC

        inst = self._get_mode_instance(mode_name)
        if inst is None:
            return tpl.HELP_MODE_NOT_FOUND.format(mode_name=mode_name)
        return inst.helper()

    def all_modes(self, arg=None):
        self._ensure_modes_available()
        message = tpl.MODES_LIST_HEADER
        for mode_name, description in self.modes_descriptions.items():
            message += tpl.MODES_LIST_ITEM.format(
                mode_name=mode_name,
                description=description,
            )
        return message
