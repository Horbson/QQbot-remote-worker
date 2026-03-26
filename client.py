# -*- coding: utf-8 -*-
import asyncio
import os
import subprocess
import json
from utils import generate_random_code
from utils.data import get_supervisor_openid, set_supervisor_openid

import botpy
from botpy import logging
from botpy.ext.cog_yaml import read
from botpy.message import C2CMessage
from botpy.types.message import MarkdownPayload

_log = logging.get_logger()

class MyClient(botpy.Client):
    def __init__(self, intents=None, mode_manager=None):
        super().__init__(intents=intents)
        # 管理员绑定相关
        self.supervisor_openid = None
        self._random_code = None

        # 收消息相关
        self.sender_openid = None
        self.recv_content = None
        # 运行模式相关设置
        self.mode_manager = mode_manager

    def command_handler(self, command: str, arg: str=None):
        return self.mode_manager.handle_command(command, arg)

    async def online_notify(self):
        if hasattr(self, "supervisor_openid"):
            await self.send_c2c_text_message(
                openid=self.supervisor_openid,
                content="I am online now!"
            )

    async def on_ready(self):
        _log.info(f"「{self.robot.name}」 连接成功!")
        self.supervisor_openid = get_supervisor_openid()
        if self.supervisor_openid:
            await self.online_notify()
        else:
            await self.bind_supervisor()
            return

    async def bind_supervisor(self):
        """
        首次运行或未设置管理员时的初始化逻辑
        """
        if not self._random_code:
            self._random_code = generate_random_code()
            _log.info(f"验证码: {self._random_code}。请将验证码发送给机器人以完成管理员绑定。")
            return False
        else:
            if self.recv_content == self._random_code:
                self.supervisor_openid = self.sender_openid
                os.makedirs("data", exist_ok=True)
                set_supervisor_openid(self.supervisor_openid)
                _log.info(f"管理员绑定: OpenID={self.supervisor_openid}")
                await self.online_notify()
                return True
            else:
                _log.info(f"收到错误的验证码。正确的验证码: {self._random_code}, 收到的内容: {self.recv_content}。")
                return False

    async def is_authorized(self, sender_openid):
        if self.supervisor_openid is None:
            return False
        
        if sender_openid != self.supervisor_openid:
            return False
        
        return True

    async def on_c2c_message_create(self, message: C2CMessage):
        self.recv_content = message.content
        self.sender_openid = message.author.user_openid

        _log.info(f"Received message \"{self.recv_content}\" from OpenID={self.sender_openid}.")

        if not await self.is_authorized(self.sender_openid):
            if not await self.bind_supervisor():
                send_content = "Unauthorized."
            else:
                send_content = "绑定成功。"
        else:
            # 管理员已绑定，处理消息
            # 处理命令
            if self.recv_content.startswith("/"):
                proc_content = self.recv_content[1:].split(" ", 1)
                send_content = self.command_handler(proc_content[0], proc_content[1] if len(proc_content)>1 else None)
            # 处理非命令消息
            else:
                send_content = self.mode_manager.message_handler(self.recv_content)
        
        await self.send_c2c_text_message(
            openid = self.sender_openid,
            content = send_content,
            msg_type=2
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

