from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sublingo.core.config import AppConfig
from sublingo.core.models import BilingualEntry, SubtitleEntry
from sublingo.core.translator import translate


class ProgressSpy:
    def __init__(self) -> None:
        self.events: list[tuple[int, int, str, dict[str, Any]]] = []

    def on_progress(
        self, current: int, total: int, message: str = "", **meta: Any
    ) -> None:
        self.events.append((current, total, message, meta))

    def on_log(self, level: str, message: str, detail: str = "") -> None:
        return None


class FakeAiClient:
    instances: list[FakeAiClient] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.max_retries = 0
        self.segment_calls = 0
        self.translate_calls: list[dict[str, Any]] = []
        self.proofread_calls: list[dict[str, Any]] = []
        self.detect_value = "en"
        FakeAiClient.instances.append(self)

    async def segment_entries(
        self,
        entries: list[SubtitleEntry],
        *,
        temperature: float,
    ) -> list[SubtitleEntry]:
        self.segment_calls += 1
        assert isinstance(temperature, float)
        return [SubtitleEntry(start_ms=0, end_ms=1000, text="hello world")]

    async def detect_language(self, sample_text: str) -> str:
        assert isinstance(sample_text, str)
        return self.detect_value

    async def translate_batch(
        self,
        entries: list[SubtitleEntry],
        *,
        target_lang: str,
        glossary_text: str = "",
        temperature: float,
    ) -> list[str]:
        self.translate_calls.append(
            {
                "entries": entries,
                "target_lang": target_lang,
                "glossary_text": glossary_text,
                "temperature": temperature,
            }
        )
        return [f"{entry.text}-{target_lang}" for entry in entries]

    async def proofread_batch(
        self,
        entries: list[BilingualEntry],
        *,
        context_entries: list[BilingualEntry],
        glossary_text: str = "",
        temperature: float,
    ) -> list[str]:
        self.proofread_calls.append(
            {
                "entries": entries,
                "context_entries": context_entries,
                "glossary_text": glossary_text,
                "temperature": temperature,
            }
        )
        return [f"{entry.translated}-ok" for entry in entries]

    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def patch_ai_client(monkeypatch: pytest.MonkeyPatch):
    FakeAiClient.instances = []
    monkeypatch.setattr("sublingo.core.translator.AiClient", FakeAiClient)


def make_config() -> AppConfig:
    return AppConfig(
        ai_base_url="https://api.example.com/v1",
        ai_model="gpt-test",
        ai_api_key="secret",
        ai_translate_batch_size=1,
        ai_proofread_batch_size=1,
        ai_max_retries=5,
        font_file="LXGWWenKai-Medium.ttf",
    )


@pytest.mark.asyncio
async def test_translate_runs_full_pipeline_and_writes_output(tmp_path: Path):
    subtitle_path = tmp_path / "sample.en.vtt"
    subtitle_path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n\n00:00:02.500 --> 00:00:03.500\nWorld\n",
        encoding="utf-8",
    )
    glossary_path = tmp_path / "g.csv"
    glossary_path.write_text("source,target\nHello,你好\n", encoding="utf-8")
    spy = ProgressSpy()

    result = await translate(
        subtitle_path,
        target_lang="zh-Hans",
        ai_config=make_config(),
        glossary_path=glossary_path,
        output_dir=tmp_path,
        progress=spy,
    )

    assert result.success is True
    assert result.output_path == tmp_path / "sample.en.zh-Hans.ass"
    assert result.output_path is not None
    assert result.output_path.exists()
    assert "Hello-zh-Hans-ok" in result.output_path.read_text(encoding="utf-8")
    assert (tmp_path / ".checkpoint.json").exists()
    checkpoint = json.loads((tmp_path / ".checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["translated_batches"] == 2
    assert checkpoint["total_batches"] == 2
    assert len(checkpoint["entries"]) == 2
    assert len(spy.events) == 4

    fake = FakeAiClient.instances[0]
    assert fake.max_retries == 5
    assert "Hello => 你好" in fake.translate_calls[0]["glossary_text"]
    assert len(fake.proofread_calls) == 2


@pytest.mark.asyncio
async def test_translate_auto_generated_uses_segmentation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    subtitle_path = tmp_path / "auto.en.vtt"
    subtitle_path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:00.200\nA\n\n00:00:00.150 --> 00:00:00.300\nB\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sublingo.core.translator.is_auto_generated", lambda _: True)

    result = await translate(
        subtitle_path,
        target_lang="zh-Hans",
        ai_config=make_config(),
        output_dir=tmp_path,
    )

    assert result.success is True
    fake = FakeAiClient.instances[0]
    assert fake.segment_calls == 1


@pytest.mark.asyncio
async def test_translate_returns_warning_when_source_equals_target(tmp_path: Path):
    subtitle_path = tmp_path / "same.en.vtt"
    subtitle_path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n",
        encoding="utf-8",
    )

    config = make_config()
    result_task = translate(
        subtitle_path,
        target_lang="en-US",
        ai_config=config,
        output_dir=tmp_path,
    )
    fake = FakeAiClient.instances[0] if FakeAiClient.instances else None
    if fake is not None:
        fake.detect_value = "en"
    result = await result_task

    assert result.success is True
    assert result.output_path is None
    assert result.warnings
    assert (tmp_path / "same.en.en-US.ass").exists() is False


@pytest.mark.asyncio
async def test_translate_requires_api_key(tmp_path: Path):
    subtitle_path = tmp_path / "sample.vtt"
    subtitle_path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n",
        encoding="utf-8",
    )
    config = make_config()
    config.ai_api_key = ""

    result = await translate(subtitle_path, target_lang="zh-Hans", ai_config=config)

    assert result.success is False
    assert "API key" in str(result.error)


@pytest.mark.asyncio
async def test_translate_fails_on_empty_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    subtitle_path = tmp_path / "sample.vtt"
    subtitle_path.write_text("WEBVTT\n\n", encoding="utf-8")
    monkeypatch.setattr("sublingo.core.translator.parse_subtitle", lambda _: [])

    result = await translate(
        subtitle_path,
        target_lang="zh-Hans",
        ai_config=make_config(),
    )

    assert result.success is False
    assert "No subtitle entries" in str(result.error)
