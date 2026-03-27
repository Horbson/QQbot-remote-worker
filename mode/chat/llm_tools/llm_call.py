from openai import OpenAI
from dotenv import load_dotenv
import os

def message_generator(streamIter, including_reasoning=True):
    """
    将流式响应转换成一个流式生成消息的生成器。
    """
    for chunk in streamIter:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content"):
            if not including_reasoning:
                continue
            yield {"type": "thinking", "content": delta.reasoning_content, "role": "assistant"}
        elif delta.content:
            yield {"type": "chat", "content": delta.content, "role": "assistant"}
        else:
            continue


def call_llm(
    context: list[dict],
    model: str = "deepseek-chat",
    temperature: float = 0.5,
    max_token: int = 4096,
    thinking: bool = True,
    stream: bool = False
):
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    client = OpenAI(api_key = api_key, base_url = base_url)
    try:
        response = client.chat.completions.create(
            model = model,
            messages = context,
            temperature = temperature,
            max_tokens = max_token,
            extra_body = {"thinking": {"type": "enabled" if thinking else "disabled"}},
            stream = stream
        )
    except Exception as e:
        print(e)
        return None

    if stream:
        return response
    else:
        message = response.choices[0].message
        return {
            "reasoning_content": message.get("reasoning_content"),
            "content": message.content,
            "full_response_body": response
        }

if __name__ == "__main__":
    test_context = [
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": "介绍下你自己"}
    ]
    result = call_llm(context = test_context, stream = True, thinking=False)
    status  = "start"
    for delta in message_generator(result):
        new_status = delta["type"]
        if new_status == "thinking" and status == "start":
            print("<thinking>")
        elif new_status == "chat" and status == "thinking":
            print("\n</thinking>")
        print(delta["content"], end = "")
        status = new_status
