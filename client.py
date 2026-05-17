# -*- coding: utf-8 -*-
import asyncio
import os

import botpy
from botpy import logging
from botpy.message import C2CMessage

from utils import generate_random_code
from utils.data import get_supervisor_openid, set_supervisor_openid
from utils.error_handler import SystemError, handle_error
from utils.reply import BotReply, ReplyType, normalize_reply

_log = logging.get_logger(__name__)


class MessageSendError(SystemError):
    """Raised when the bot cannot send a reply after retries."""
    pass


class MyClient(botpy.Client):
    def __init__(self, intents=None, mode_manager=None):
        super().__init__(intents=intents)
        self.supervisor_openid = None
        self._random_code = None

        self.sender_openid = None
        self.recv_content = None
        self.mode_manager = mode_manager

    def command_handler(self, message: C2CMessage):
        return self.mode_manager.handle_command(message)

    def message_handler(self, message: C2CMessage):
        return self.mode_manager.message_handler(message)

    async def online_notify(self):
        if not self.supervisor_openid:
            return
        await self.send_c2c_text_message(
            openid=self.supervisor_openid,
            content="I am online now!",
        )

    async def on_ready(self):
        _log.info(f"「{self.robot.name}」 connected.")
        self.supervisor_openid = get_supervisor_openid()
        if self.supervisor_openid:
            await self.online_notify()
            return
        await self.bind_supervisor()

    async def bind_supervisor(self):
        """Bind the first verified sender as supervisor."""
        if not self._random_code:
            self._random_code = generate_random_code()
            _log.info(
                f"Supervisor verification code: {self._random_code}. "
                "Send this code to the bot to finish binding."
            )
            return False

        if self.recv_content != self._random_code:
            _log.info(
                "Received invalid supervisor verification code. "
                f"expected={self._random_code}, actual={self.recv_content}"
            )
            return False

        self.supervisor_openid = self.sender_openid
        os.makedirs("data", exist_ok=True)
        set_supervisor_openid(self.supervisor_openid)
        _log.info(f"Supervisor bound: OpenID={self.supervisor_openid}")
        await self.online_notify()
        return True

    async def is_authorized(self, sender_openid):
        return bool(self.supervisor_openid and sender_openid == self.supervisor_openid)

    async def on_c2c_message_create(self, message: C2CMessage):
        self.recv_content = message.content
        self.sender_openid = message.author.user_openid

        _log.info(
            f"Received message from OpenID={self.sender_openid}: "
            f"{self.recv_content!r}"
        )

        try:
            reply = await self._build_reply(message)
        except Exception as e:
            result = handle_error(e, "处理 C2C 消息", "处理消息失败，请稍后重试。")
            reply = BotReply.markdown_text(result["message"])

        _log.info(f"Sending reply preview: {reply}")
        await self.send_c2c_reply(
            openid=self.sender_openid,
            reply=reply,
        )

    async def _build_reply(self, message: C2CMessage):
        if not await self.is_authorized(self.sender_openid):
            if await self.bind_supervisor():
                return BotReply.plaintext("绑定成功。")
            return BotReply.plaintext("Unauthorized.")

        if self.recv_content.startswith("/"):
            return self.command_handler(message)

        return self.message_handler(message)

    async def send_c2c_text_message(self, openid, content, msg_type=0):
        if msg_type == ReplyType.MARKDOWN:
            reply = BotReply.markdown_text(content)
        else:
            reply = BotReply(msg_type=msg_type, content=content)
        return await self.send_c2c_reply(openid, reply)

    async def send_c2c_reply(self, openid, reply):
        reply = normalize_reply(reply)
        last_error = None
        for retry_count in range(7):
            try:
                result = await self._post_c2c_reply(openid, reply)
            except Exception as e:
                last_error = e
                result = None
                _log.warning(f"Failed to send message to {openid}: {e}")

            if result:
                _log.info(
                    f"Message sent successfully to {openid}, "
                    f"with retry count: {retry_count}"
                )
                return True

            if retry_count >= 6:
                break

            _log.warning("Failed to send message, retrying...")
            await asyncio.sleep(min(2 ** retry_count, 10))

        if last_error is not None:
            _log.error(f"Failed to send message to {openid} after retries: {last_error}")
            raise MessageSendError(f"Failed to send message to {openid}") from last_error
        _log.error(f"Failed to send message to {openid} after retries.")
        raise MessageSendError(f"Failed to send message to {openid} after retries.")

    async def _post_c2c_reply(self, openid, reply: BotReply):
        if int(reply.msg_type) == ReplyType.FILE:
            if reply.file_type is None or not reply.file_url:
                raise ValueError("File replies require file_type and file_url")

            media = await self.api.post_c2c_file(
                openid=openid,
                file_type=reply.file_type,
                url=reply.file_url,
                srv_send_msg=reply.srv_send_msg,
            )
            if not media:
                return media
            if reply.srv_send_msg:
                return media
            return await self.api.post_c2c_message(
                openid=openid,
                **BotReply.from_media(media).to_message_kwargs(),
            )

        return await self.api.post_c2c_message(
            openid=openid,
            **reply.to_message_kwargs(),
        )
