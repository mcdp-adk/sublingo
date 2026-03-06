from __future__ import annotations

import json
import math
import random
import re
from typing import Any

import anyio
import httpx

from sublingo.core.constants import (
    AI_BASE_DELAY,
    AI_HTTP_TIMEOUT_CONNECT,
    AI_HTTP_TIMEOUT_TOTAL,
    AI_MAX_RETRIES,
    AI_MAX_TOKENS_DEFAULT,
    AI_MAX_TOKENS_LANGUAGE_DETECT,
    AI_TEMPERATURE_LANGUAGE_DETECT,
)
from sublingo.core.models import BilingualEntry, SubtitleEntry

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")
JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


class AiClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        proxy: str | None = None,
        trust_env: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_retries = AI_MAX_RETRIES
        self.base_delay = AI_BASE_DELAY
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                AI_HTTP_TIMEOUT_TOTAL, connect=AI_HTTP_TIMEOUT_CONNECT
            ),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            proxy=proxy,
            trust_env=trust_env,
        )

    async def translate_batch(
        self,
        entries: list[SubtitleEntry],
        *,
        target_lang: str,
        glossary_text: str = "",
        temperature: float,
    ) -> list[str]:
        if not entries:
            return []
        system = _build_translation_system_prompt(target_lang, glossary_text)
        payload = [{"index": i, "text": entry.text} for i, entry in enumerate(entries)]
        user = (
            "Translate subtitle entries. Respond only JSON array of strings in original order:\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        content = await self._chat_completion(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=AI_MAX_TOKENS_DEFAULT,
        )
        translations = _parse_string_array(content)
        if len(translations) != len(entries):
            raise ValueError(
                f"Translation count mismatch: expected {len(entries)}, got {len(translations)}"
            )
        return translations

    async def detect_language(self, sample_text: str) -> str:
        prompt = (
            "You are a language detector. Identify the primary language of subtitle text. "
            'Return JSON object only: {"language": "<ISO 639-1>"}. '
            "No explanation."
        )
        content = await self._chat_completion(
            system=prompt,
            user=f"Sample text:\n{sample_text[:2000]}",
            temperature=AI_TEMPERATURE_LANGUAGE_DETECT,
            max_tokens=AI_MAX_TOKENS_LANGUAGE_DETECT,
        )
        data = _parse_json_value(content)
        if isinstance(data, dict):
            language = str(data.get("language", "unknown")).strip().lower()
            return language or "unknown"
        return "unknown"

    async def proofread_batch(
        self,
        entries: list[BilingualEntry],
        *,
        context_entries: list[BilingualEntry],
        glossary_text: str = "",
        temperature: float,
    ) -> list[str]:
        if not entries:
            return []
        system = _build_proofread_system_prompt(glossary_text)
        context_payload = [
            {
                "original": entry.original,
                "translated": entry.translated,
            }
            for entry in context_entries
        ]
        batch_payload = [
            {
                "index": i,
                "original": entry.original,
                "translated": entry.translated,
            }
            for i, entry in enumerate(entries)
        ]
        user = (
            "Proofread current batch using context. Keep meaning and timing fit. "
            "Return only JSON array of strings in current batch order.\n"
            f"Context:\n{json.dumps(context_payload, ensure_ascii=False)}\n"
            f"Batch:\n{json.dumps(batch_payload, ensure_ascii=False)}"
        )
        content = await self._chat_completion(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=AI_MAX_TOKENS_DEFAULT,
        )
        translations = _parse_string_array(content)
        if len(translations) != len(entries):
            raise ValueError(
                f"Proofread count mismatch: expected {len(entries)}, got {len(translations)}"
            )
        return translations

    async def segment_entries(
        self,
        entries: list[SubtitleEntry],
        *,
        temperature: float,
    ) -> list[SubtitleEntry]:
        if not entries:
            return []
        payload = [{"index": i, "text": e.text} for i, e in enumerate(entries)]
        system = (
            "You segment auto-generated subtitle fragments into sentence-level lines. "
            "Do not change order, do not drop content. "
            "Return JSON array of arrays. "
            "Each inner array contains original indices grouped as one sentence."
        )
        user = (
            "Group indices into sentence-level segments. Return only JSON.\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        content = await self._chat_completion(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=AI_MAX_TOKENS_DEFAULT,
        )
        groups = _parse_index_groups(content)
        return _merge_entries(entries, groups)

    async def test_connection(self) -> tuple[bool, str]:
        try:
            content = await self._chat_completion(
                system="You are a connectivity test assistant.",
                user="Reply with OK.",
                temperature=0.0,
                max_tokens=8,
            )
            return True, content
        except Exception as exc:
            return False, str(exc)

    async def close(self) -> None:
        await self._http.aclose()

    async def _chat_completion(
        self,
        *,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None
        for retry in range(self.max_retries):
            try:
                response = await self._http.post(url, json=payload)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_error = exc
                if retry == self.max_retries - 1:
                    break
                await anyio.sleep(self._retry_delay(retry))
                continue

            if response.status_code == 429 or response.status_code >= 500:
                last_error = RuntimeError(f"HTTP {response.status_code}")
                if retry == self.max_retries - 1:
                    break
                await anyio.sleep(self._retry_delay(retry))
                continue

            if response.status_code != 200:
                raise RuntimeError(_extract_error_message(response))

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                chunks = [
                    str(item.get("text", ""))
                    for item in content
                    if isinstance(item, dict)
                ]
                return "".join(chunks)
            return str(content)

        raise RuntimeError(f"AI API call failed after retries: {last_error}")

    def _retry_delay(self, retry: int) -> float:
        return min(self.base_delay * math.pow(2, retry) + random.random(), 60.0)


def _build_translation_system_prompt(target_lang: str, glossary_text: str) -> str:
    rules = [
        "You are a professional subtitle translator.",
        f"Translate to {target_lang}.",
        "Keep meaning, tone, and natural subtitle rhythm.",
        "Return only JSON array of translated strings.",
    ]
    if _is_chinese_target(target_lang):
        rules.extend(
            [
                "Chinese Netflix rules: max 16 chars per line.",
                "Chinese Netflix rules: no commas or periods.",
                "Chinese Netflix rules: use a single space when needed.",
            ]
        )
    if glossary_text:
        rules.append(glossary_text)
    return "\n".join(rules)


def _build_proofread_system_prompt(glossary_text: str) -> str:
    rules = [
        "You are a subtitle proofreader.",
        "Improve fluency and consistency without changing intent.",
        "Return only JSON array of proofread translated strings.",
    ]
    if glossary_text:
        rules.append(glossary_text)
    return "\n".join(rules)


def _is_chinese_target(target_lang: str) -> bool:
    value = target_lang.lower()
    return value.startswith("zh") or "chinese" in value


def _parse_json_value(content: str) -> Any:
    stripped = content.strip()
    if not stripped:
        raise ValueError("Empty response")
    markdown = JSON_BLOCK_RE.search(stripped)
    if markdown:
        return json.loads(markdown.group(1).strip())
    array_match = JSON_ARRAY_RE.search(stripped)
    if array_match and stripped[0] != "[":
        return json.loads(array_match.group(0))
    return json.loads(stripped)


def _parse_string_array(content: str) -> list[str]:
    value = _parse_json_value(content)
    if isinstance(value, dict) and isinstance(value.get("translations"), list):
        value = value["translations"]
    if not isinstance(value, list):
        raise ValueError("Expected JSON array response")
    return [str(item) for item in value]


def _parse_index_groups(content: str) -> list[list[int]]:
    value = _parse_json_value(content)
    if not isinstance(value, list):
        raise ValueError("Expected list of index groups")
    groups: list[list[int]] = []
    for group in value:
        if isinstance(group, list):
            normalized = [int(index) for index in group]
            if normalized:
                groups.append(normalized)
    if not groups:
        raise ValueError("Empty segmentation groups")
    return groups


def _merge_entries(
    entries: list[SubtitleEntry], groups: list[list[int]]
) -> list[SubtitleEntry]:
    merged: list[SubtitleEntry] = []
    for group in groups:
        first = entries[group[0]]
        last = entries[group[-1]]
        text_parts = [
            entries[index].text.strip()
            for index in group
            if entries[index].text.strip()
        ]
        text = " ".join(text_parts).strip()
        if not text:
            continue
        merged.append(
            SubtitleEntry(start_ms=first.start_ms, end_ms=last.end_ms, text=text)
        )
    return merged


def _extract_error_message(response: httpx.Response) -> str:
    default = f"AI API call failed with HTTP {response.status_code}"
    try:
        payload = response.json()
    except Exception:
        return default
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return default
