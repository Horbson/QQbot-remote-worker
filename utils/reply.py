from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping


class ReplyType(IntEnum):
    TEXT = 0
    MARKDOWN = 2
    ARK = 3
    EMBED = 4
    MEDIA = 7
    FILE = 100


@dataclass(frozen=True)
class BotReply:
    msg_type: int
    content: str | None = None
    markdown_payload: Mapping[str, Any] | None = None
    embed: Mapping[str, Any] | None = None
    ark: Mapping[str, Any] | None = None
    media: Mapping[str, Any] | None = None
    keyboard: Mapping[str, Any] | None = None
    message_reference: Mapping[str, Any] | None = None
    file_type: int | None = None
    file_url: str | None = None
    srv_send_msg: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def plaintext(cls, content: str):
        return cls(msg_type=ReplyType.TEXT, content=content)

    @classmethod
    def markdown_text(cls, content: str):
        return cls(
            msg_type=ReplyType.MARKDOWN,
            markdown_payload={"content": content},
        )

    @classmethod
    def from_markdown(cls, payload: Mapping[str, Any]):
        return cls(msg_type=ReplyType.MARKDOWN, markdown_payload=payload)

    @classmethod
    def from_embed(cls, payload: Mapping[str, Any]):
        return cls(msg_type=ReplyType.EMBED, embed=payload)

    @classmethod
    def from_ark(cls, payload: Mapping[str, Any]):
        return cls(msg_type=ReplyType.ARK, ark=payload)

    @classmethod
    def from_media(cls, payload: Mapping[str, Any]):
        return cls(msg_type=ReplyType.MEDIA, media=payload)

    @classmethod
    def from_file(cls, file_type: int, url: str, srv_send_msg: bool = False):
        return cls(
            msg_type=ReplyType.FILE,
            file_type=file_type,
            file_url=url,
            srv_send_msg=srv_send_msg,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]):
        data = dict(payload)
        msg_type = data.pop("msg_type")
        generic_payload = data.pop("payload", None)

        if "plaintext" in data and "content" not in data:
            data["content"] = data.pop("plaintext")
        if "markdown" in data and "markdown_payload" not in data:
            data["markdown_payload"] = data.pop("markdown")
        if "url" in data and "file_url" not in data:
            data["file_url"] = data.pop("url")
        if generic_payload is not None:
            if int(msg_type) == ReplyType.TEXT and "content" not in data:
                if isinstance(generic_payload, Mapping):
                    data["content"] = generic_payload.get("content")
                else:
                    data["content"] = generic_payload
            elif int(msg_type) == ReplyType.MARKDOWN and "markdown_payload" not in data:
                data["markdown_payload"] = generic_payload
            elif int(msg_type) == ReplyType.ARK and "ark" not in data:
                data["ark"] = generic_payload
            elif int(msg_type) == ReplyType.EMBED and "embed" not in data:
                data["embed"] = generic_payload
            elif int(msg_type) == ReplyType.MEDIA and "media" not in data:
                data["media"] = generic_payload
            elif int(msg_type) == ReplyType.FILE and isinstance(generic_payload, Mapping):
                data.setdefault("file_type", generic_payload.get("file_type"))
                data.setdefault("file_url", generic_payload.get("url"))
                data.setdefault(
                    "srv_send_msg",
                    generic_payload.get("srv_send_msg", False),
                )

        fields = {
            "content",
            "markdown_payload",
            "embed",
            "ark",
            "media",
            "keyboard",
            "message_reference",
            "file_type",
            "file_url",
            "srv_send_msg",
        }
        kwargs = {name: data.pop(name) for name in list(data) if name in fields}
        return cls(msg_type=msg_type, extra=data, **kwargs)

    def to_message_kwargs(self):
        if int(self.msg_type) == ReplyType.FILE:
            raise ValueError("File replies must be uploaded before sending a message")

        kwargs: dict[str, Any] = {"msg_type": int(self.msg_type)}
        optional_values = {
            "content": self.content,
            "markdown": self.markdown_payload,
            "embed": self.embed,
            "ark": self.ark,
            "media": self.media,
            "keyboard": self.keyboard,
            "message_reference": self.message_reference,
        }
        kwargs.update(
            {name: value for name, value in optional_values.items() if value is not None}
        )
        kwargs.update(self.extra)
        return kwargs


def normalize_reply(reply: BotReply | Mapping[str, Any] | str) -> BotReply:
    if isinstance(reply, BotReply):
        return reply
    if isinstance(reply, str):
        return BotReply.markdown_text(reply)
    if isinstance(reply, Mapping):
        return BotReply.from_mapping(reply)
    raise TypeError(f"Unsupported reply type: {type(reply).__name__}")
