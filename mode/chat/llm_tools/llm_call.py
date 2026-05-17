import os

from botpy import logging
from dotenv import load_dotenv
from openai import APIConnectionError, AuthenticationError, OpenAI, OpenAIError, RateLimitError

from utils.error_handler import ConfigurationError, NetworkError, PermissionError

_log = logging.get_logger(__name__)


def resolve_model_id(model_id: str | None = None) -> str:
    resolved_model_id = model_id or os.getenv("OPENAI_MODEL_ID")
    if not resolved_model_id:
        raise ConfigurationError("缺少 OPENAI_MODEL_ID 配置")
    return resolved_model_id


def call_llm(
    context: list[dict],
    model_id: str | None = None,
    temperature: float = 0.5,
    max_token: int = 4096,
    reasoning_effort: str | None = "medium",
    stream: bool = False,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
    parallel_tool_calls: bool = False,
):
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    resolved_model_id = resolve_model_id(model_id)

    if not api_key:
        raise ConfigurationError("缺少 OPENAI_API_KEY 配置")
    if not base_url:
        raise ConfigurationError("缺少 OPENAI_BASE_URL 配置")

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        request_kwargs = {
            "model": resolved_model_id,
            "messages": context,
            "temperature": temperature,
            "max_tokens": max_token,
            "stream": stream,
        }
        if reasoning_effort is not None:
            request_kwargs["reasoning_effort"] = reasoning_effort
        if tools is not None:
            request_kwargs["tools"] = tools
            request_kwargs["parallel_tool_calls"] = parallel_tool_calls
        if tool_choice is not None:
            request_kwargs["tool_choice"] = tool_choice

        response = client.chat.completions.create(**request_kwargs)
    except RateLimitError as e:
        _log.warning(f"LLM rate limited: {e}")
        raise NetworkError("请求过于频繁，请稍后重试") from e
    except AuthenticationError as e:
        _log.error(f"LLM authentication failed: {e}")
        raise PermissionError("AI 服务认证失败，请检查 API 密钥配置") from e
    except APIConnectionError as e:
        _log.error(f"LLM connection failed: {e}")
        raise NetworkError("无法连接到 AI 服务，请检查网络连接") from e
    except OpenAIError as e:
        _log.exception(f"OpenAI-compatible API error: {e}")
        raise NetworkError("AI 服务响应异常，请稍后重试") from e
    except Exception as e:
        _log.exception(f"Unexpected LLM error: {e}")
        raise

    if stream:
        return response

    message = response.choices[0].message
    tool_calls = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        tool_calls.append({
            "id": tool_call.id,
            "type": tool_call.type,
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        })

    assistant_message = {
        "role": "assistant",
        "content": message.content or "",
    }
    if tool_calls:
        assistant_message["tool_calls"] = tool_calls

    return {
        "reasoning_content": message.reasoning_content if hasattr(message, "reasoning_content") else "",
        "content": message.content,
        "tool_calls": tool_calls,
        "message": assistant_message,
        "full_response_body": response,
    }
