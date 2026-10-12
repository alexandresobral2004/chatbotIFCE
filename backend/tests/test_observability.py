import asyncio

import pytest

from core import observability
from ports.usage_log_port import UsageLogPort


class FakeUsageLog(UsageLogPort):
    def __init__(self):
        self.rows = []

    async def log_usage(self, provider, model, input_tokens, output_tokens, total_cost, latency_ms,
                        user_id=None, endpoint=None):
        self.rows.append(dict(provider=provider, model=model, input_tokens=input_tokens,
                              output_tokens=output_tokens, user_id=user_id, endpoint=endpoint))
        return "id-1"


class FakeLLM:
    model = "gpt-4o-mini"

    def __init__(self, usage_adapter):
        self.usage_adapter = usage_adapter

    @observability.track_llm_usage("openai", "chat_test")
    async def complete(self, messages, **kwargs):
        return {"content": "resposta curta"}

    @observability.track_llm_usage("openai", "chat_stream_test")
    async def stream(self, messages, stream=True, **kwargs):
        for piece in ("uma ", "resposta ", "em partes"):
            yield piece

    @observability.track_llm_usage("openai")
    async def generate_embedding(self, text):
        return [0.1, 0.2]


@pytest.fixture(autouse=True)
def offline_tokens(monkeypatch):
    # tiktoken baixa o vocabulário na primeira execução; nos testes contamos palavras.
    monkeypatch.setattr(observability, "count_tokens", lambda text, model="x": len(str(text).split()))


def run(coro):
    return asyncio.run(coro)


def test_usage_adapter_is_a_port_not_a_concrete_adapter():
    from adapters.postgres_usage_adapter import PostgresUsageAdapter

    assert issubclass(PostgresUsageAdapter, UsageLogPort)


def test_non_stream_call_logs_tokens_and_attributes_user():
    log = FakeUsageLog()
    llm = FakeLLM(log)
    result = run(llm.complete([{"role": "user", "content": "duas palavras"}], user_id="u-7"))
    assert result == {"content": "resposta curta"}
    assert log.rows == [dict(provider="openai", model="gpt-4o-mini", input_tokens=2, output_tokens=2,
                             user_id="u-7", endpoint="chat_test")]


def test_stream_call_logs_after_the_stream_ends():
    log = FakeUsageLog()
    llm = FakeLLM(log)

    async def consume():
        return [c async for c in llm.stream([{"role": "user", "content": "oi"}], stream=True)]

    assert run(consume()) == ["uma ", "resposta ", "em partes"]
    assert len(log.rows) == 1 and log.rows[0]["output_tokens"] == 4  # "uma resposta em partes"
    assert log.rows[0]["endpoint"] == "chat_stream_test"


def test_embeddings_have_no_output_tokens_and_default_endpoint_is_the_function_name():
    log = FakeUsageLog()
    run(FakeLLM(log).generate_embedding("um texto de entrada"))
    assert log.rows[0]["output_tokens"] == 0 and log.rows[0]["endpoint"] == "generate_embedding"


def test_without_a_usage_adapter_the_call_still_works():
    assert run(FakeLLM(None).complete([{"role": "user", "content": "oi"}])) == {"content": "resposta curta"}
