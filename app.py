# -*- coding: utf-8 -*-
import asyncio
import os
import subprocess
import json
from utils import generate_random_code

import botpy
from botpy import logging
from botpy.ext.cog_yaml import read
from botpy.message import C2CMessage
from botpy.manage import GroupManageEvent
from botpy.types.message import MarkdownPayload

from llm_tools import call_llm 

from dotenv import load_dotenv

load_dotenv()

test_config = {"appid": os.getenv("qqbot_appid"), "secret": os.getenv("qqbot_appsecret")}

_log = logging.get_logger()

receive_confirm_markdown_template = """# Message Received
- Content: {content}
- Retry Count: {retry_count}
- Your OpenID: {openid}"""

exec_result_markdown_template = """# Command Execution Result
- Command: {command}
- Return Code: {returncode}
- Output: {stdout}
- Error Output: {stderr}"""

class MyClient(botpy.Client):
    def __init__(self, intents=None, modes: dict=None):
        super().__init__(intents=intents)
        # 管理员绑定相关
        self.supervisor_openid = None
        self.supervisor_binding_flag = False
        self.__random_code = generate_random_code()

        # 运行模式相关设置
        self.__modes_titles = list(modes)
        self.__modes = modes
        self.__modes_count = len(self.__modes_titles)
        self.__current_mode_index = 0
        self.__current_mode_title = self.__modes_titles[0]
        self.__current_mode_handler = self.__modes[self.__current_mode_title]["handler"]

    def __switch_mode(self, next_mode_title = None):
        if next_mode_title:
            if next_mode_title not in self.__modes_titles:
                return "Target mode has not been registried."
            self.__current_mode_title = next_mode_title
            self.__current_mode_index = self.__modes_titles.index(self.__current_mode_title)
        else:
            self.__current_mode_index = (self.__current_mode_index + 1) % self.__modes_count
            self.__current_mode_title = self.__modes_titles[self.__current_mode_index]

        self.__current_mode_handler = self.__modes[self.__current_mode_title]["handler"]

        return f"Switched to {self.__current_mode_title} mode."

    def __helper(self, target = None):
        return "modes, switch, active_mode, help"

    def command_handler(self, command: str, arg: str=None):
        command_handler_map = {
            "switch": self.__switch_mode,
            "modes" : lambda _: "Available modes include:\n" + "\n".join(self.__modes_titles),
            "active_mode": lambda _: f"{self.__current_mode_title} mode is activate now.",
            "help": self.__helper,
            "hi": lambda _: "Hello!"
        }
        if command not in command_handler_map:
            return "Invalid command." + command_handler_map["modes"](None)
        return command_handler_map[command](arg)

    async def initializer(self, received_content=None, sender_openid=None):
        # 首次运行或未设置管理员时的初始化逻辑
        if not self.supervisor_binding_flag:
            _log.info(f"验证码: {self.__random_code}。请将验证码发送给机器人以完成管理员绑定。")
            self.supervisor_binding_flag = True
        else:
            if received_content == self.__random_code:
                self.supervisor_openid = sender_openid
                os.makedirs("data", exist_ok=True)
                with open("data/supervisor.json", "w") as f:
                    json.dump({"supervisor_openid": self.supervisor_openid}, f)
                _log.info(f"管理员绑定: OpenID={self.supervisor_openid}")
                await self.online_notify()
            else:
                _log.info(f"错误的验证码。")

    async def online_notify(self):
        if hasattr(self, "supervisor_openid"):
            await self.send_c2c_text_message(
                openid=self.supervisor_openid,
                content="I am online now!"
            )

    def check_supervisor(self):
        try:
            with open("data/supervisor.json", "r") as f:
                supervisor_openid = json.load(f).get("supervisor_openid")
            return supervisor_openid
        except FileNotFoundError:
            return None

    async def on_ready(self):
        _log.info(f"「{self.robot.name}」 连接成功!")
        self.supervisor_openid = self.check_supervisor()
        if self.supervisor_openid:
            await self.online_notify()
        else:
            await self.initializer()
            return

    async def on_c2c_message_create(self, message: C2CMessage):
        recv_content = message.content
        sender_openid = message.author.user_openid

        _log.info(f"Received message \"{recv_content}\" from OpenID={sender_openid}.")

        # 绑定管理员
        if self.supervisor_openid is None:
            await self.initializer(recv_content, sender_openid)
            return
        
        elif sender_openid != self.supervisor_openid:
            _log.info(f"收到未授权用户OpenID={sender_openid}的消息。已忽略，走！")
            await self.send_c2c_text_message(
                openid = sender_openid,
                content = "Denied." 
            )
            return

        # 管理员已绑定，处理消息
        # 处理命令
        if recv_content.startswith("/"):
            proc_content = recv_content[1:].split(" ")
            send_content = self.command_handler(proc_content[0], proc_content[1] if len(proc_content)>1 else None)
        # 处理非命令消息
        else:
            if self.__current_mode_handler == None:
                send_content = "Empty mode"
            else:
                send_content = self.__current_mode_handler(recv_content)
        
        await self.send_c2c_text_message(
            openid = sender_openid,
            content = send_content
        )

    async def send_c2c_text_message(self, openid, content, msg_type=0):
        retry_count = 0
        while True:
            if msg_type == 0:
                result = await self.api.post_c2c_message(
                    openid=openid, 
                    msg_type=msg_type, 
                    content=content
                )
            elif msg_type == 2:
                markdown_content = MarkdownPayload(content=content)
                result = await self.api.post_c2c_message(
                    openid=openid, 
                    msg_type=2, 
                    markdown=markdown_content
                )
            if result:
                _log.info(f"Message sent successfully to {openid}, with retry count: {retry_count}")
                break
            if retry_count >= 6:
                _log.error(f"Failed to send message to {openid} after {retry_count} attempts.")
                break
            _log.warning("Failed to send message, retrying...")
            retry_count += 1

def exec(command: str):
    result = subprocess.run(
        command,
        shell = True,
        capture_output = True,
        text = True
    )

    if result.returncode == 0:
        output = result.stdout
        status = "Success"
    else:
        output = result.stderr
        status = "Failed"

    return f"Execution {status} with return code {result.returncode}, output: \n{output}"

def chat(message):
    if not hasattr(chat, "context"):
        chat.context = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

    chat.context.append(
        {"role": "user", "content": message}
    )

    result = call_llm(context=chat.context)
    return f"<thinking>\n{result['reasoning_content']}\n</thinking>\n{result['content']}"

modes = {
    "exec": {
        "description": "Execute shell command",
        "handler": exec
    },
    "chat": {
        "description": "Chat with AI assistant.",
        "handler": chat
    }
}

def main():
    # 通过预设置的类型，设置需要监听的事件通道
    # intents = botpy.Intents.none()
    # intents.public_messages=True
    intents = botpy.Intents(public_messages=True)
    client = MyClient(intents=intents, modes=modes)
    client.run(**test_config)

if __name__ == "__main__":
    main()
