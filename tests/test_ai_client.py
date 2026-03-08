from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
import pytest

from sublingo.core.ai_client import AiClient
from sublingo.core.models import BilingualEntry, SubtitleEntry


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeAsyncClient:
    init_kwargs: dict[str, Any] = {}
    queue: list[Any] = []
    requests: list[tuple[str, dict[str, Any]]] = []
    closed = False

    def __init__(self, **kwargs: Any) -> None:
        FakeAsyncClient.init_kwargs = kwargs

    async def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
        FakeAsyncClient.requests.append((url, json))
        if not FakeAsyncClient.queue:
            raise AssertionError("Fake queue is empty")
        item = FakeAsyncClient.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        FakeAsyncClient.closed = True


@pytest.fixture(autouse=True)
def reset_fake_state(monkeypatch: pytest.MonkeyPatch):
    FakeAsyncClient.init_kwargs = {}
    FakeAsyncClient.queue = []
    FakeAsyncClient.requests = []
    FakeAsyncClient.closed = False
    monkeypatch.setattr("sublingo.core.ai_client.httpx.AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_init_sets_trust_env_and_proxy():
    client = AiClient(
        base_url="https://api.example.com/v1",
        api_key="key",
        model="gpt-test",
        proxy="http://127.0.0.1:7890",
    )

    assert FakeAsyncClient.init_kwargs["trust_env"] is True
    assert FakeAsyncClient.init_kwargs["proxy"] == "http://127.0.0.1:7890"

    await client.close()


@pytest.mark.asyncio
async def test_init_supports_disabled_system_proxy_lookup():
    client = AiClient(
        base_url="https://api.example.com/v1",
        api_key="key",
        model="gpt-test",
        proxy=None,
        trust_env=False,
    )

    assert FakeAsyncClient.init_kwargs["trust_env"] is False
    assert FakeAsyncClient.init_kwargs["proxy"] is None

    await client.close()


@pytest.mark.asyncio
async def test_translate_batch_returns_string_array():
    FakeAsyncClient.queue = [
        FakeResponse(
            200,
            {"choices": [{"message": {"content": '["你好", "世界"]'}}]},
        )
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    result = await client.translate_batch(
        [
            SubtitleEntry(start_ms=0, end_ms=1000, text="hello"),
            SubtitleEntry(start_ms=1000, end_ms=2000, text="world"),
        ],
        target_lang="zh-Hans",
        glossary_text="- hello => 你好",
        temperature=0.3,
    )

    sent_payload = FakeAsyncClient.requests[-1][1]
    system_text = sent_payload["messages"][0]["content"]
    assert "Chinese Netflix rules" in system_text
    assert "- hello => 你好" in system_text
    assert result == ["你好", "世界"]
    await client.close()


@pytest.mark.asyncio
async def test_detect_language_returns_iso_code():
    FakeAsyncClient.queue = [
        FakeResponse(200, {"choices": [{"message": {"content": '{"language":"en"}'}}]})
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    language = await client.detect_language("Hello world")

    assert language == "en"
    await client.close()


@pytest.mark.asyncio
async def test_proofread_batch_uses_context_and_returns_array():
    FakeAsyncClient.queue = [
        FakeResponse(200, {"choices": [{"message": {"content": '["修订后"]'}}]})
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    result = await client.proofread_batch(
        [BilingualEntry(start_ms=0, end_ms=1000, original="hello", translated="你好")],
        context_entries=[
            BilingualEntry(start_ms=0, end_ms=1000, original="world", translated="世界")
        ],
        glossary_text="- world => 世界",
        temperature=0.2,
    )

    body = FakeAsyncClient.requests[-1][1]
    assert "Context" in body["messages"][1]["content"]
    assert result == ["修订后"]
    await client.close()


@pytest.mark.asyncio
async def test_retry_on_429_then_success(monkeypatch: pytest.MonkeyPatch):
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("sublingo.core.ai_client.anyio.sleep", fake_sleep)
    FakeAsyncClient.queue = [
        FakeResponse(429, {"error": {"message": "rate limit"}}),
        FakeResponse(200, {"choices": [{"message": {"content": '["ok"]'}}]}),
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    result = await client.translate_batch(
        [SubtitleEntry(start_ms=0, end_ms=1000, text="a")],
        target_lang="en",
        temperature=0.1,
    )

    assert result == ["ok"]
    assert len(delays) == 1
    await client.close()


@pytest.mark.asyncio
async def test_retry_on_network_error_then_success(monkeypatch: pytest.MonkeyPatch):
    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("sublingo.core.ai_client.anyio.sleep", fake_sleep)
    FakeAsyncClient.queue = [
        httpx.ConnectError("network down"),
        FakeResponse(200, {"choices": [{"message": {"content": '{"language":"ja"}'}}]}),
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    language = await client.detect_language("こんにちは")

    assert language == "ja"
    await client.close()


@pytest.mark.asyncio
async def test_test_connection_returns_false_on_error():
    FakeAsyncClient.queue = [FakeResponse(401, {"error": {"message": "bad key"}})]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    ok, message = await client.test_connection()

    assert ok is False
    assert "bad key" in message
    await client.close()


@pytest.mark.asyncio
async def test_test_connection_normalizes_socks_dependency_hint() -> None:
    FakeAsyncClient.queue = [
        RuntimeError(
            "Using SOCKS proxy, but the 'socksio' package is not installed. "
            "Make sure to install httpx using `pip install httpx[socks]`."
        )
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    ok, message = await client.test_connection()

    assert ok is False
    assert "uv sync" in message
    assert "pip install" not in message
    await client.close()


@pytest.mark.asyncio
async def test_segment_entries_merges_indices_from_llm_response():
    FakeAsyncClient.queue = [
        FakeResponse(200, {"choices": [{"message": {"content": "[[0,1],[2]]"}}]})
    ]
    client = AiClient(base_url="https://api.example.com/v1", api_key="k", model="m")
    entries: Sequence[SubtitleEntry] = [
        SubtitleEntry(start_ms=0, end_ms=200, text="hello"),
        SubtitleEntry(start_ms=200, end_ms=400, text="world"),
        SubtitleEntry(start_ms=400, end_ms=600, text="again"),
    ]

    merged = await client.segment_entries(list(entries), temperature=0.1)

    assert merged == [
        SubtitleEntry(start_ms=0, end_ms=400, text="hello world"),
        SubtitleEntry(start_ms=400, end_ms=600, text="again"),
    ]
    await client.close()
