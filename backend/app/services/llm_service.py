import logging
import time

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)


async def send_message(
    messages: list[dict],
    system_prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    full_messages = [{"role": "system", "content": system_prompt}, *messages]
    temp = temperature if temperature is not None else settings.llm_temperature
    tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

    start = time.monotonic()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=full_messages,
        temperature=temp,
        max_tokens=tokens,
    )
    elapsed = time.monotonic() - start

    usage = response.usage
    logger.info(
        "LLM request: model=%s tokens_in=%s tokens_out=%s latency=%.2fs",
        settings.llm_model,
        usage.prompt_tokens if usage else "?",
        usage.completion_tokens if usage else "?",
        elapsed,
    )

    return response.choices[0].message.content


async def stream_message(
    messages: list[dict],
    system_prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    full_messages = [{"role": "system", "content": system_prompt}, *messages]
    temp = temperature if temperature is not None else settings.llm_temperature
    tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=full_messages,
        temperature=temp,
        max_tokens=tokens,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
