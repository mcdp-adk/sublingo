from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from sublingo.core.ai_client import AiClient
from sublingo.core.config import AppConfig
from sublingo.core.network_policy import resolve_http_proxy_policy
from sublingo.core.constants import (
    AI_LANGUAGE_DETECT_SAMPLE_LENGTH,
    AI_TEMPERATURE_DEFAULT,
    AI_TEMPERATURE_PROOFREADING,
    AI_TEMPERATURE_SEGMENTATION,
)
from sublingo.core.glossary import format_glossary_for_prompt, load_glossary
from sublingo.core.models import (
    BilingualEntry,
    ProgressCallback,
    SubtitleEntry,
    TranslateResult,
)
from sublingo.core.subtitle import (
    generate_bilingual_ass,
    is_auto_generated,
    parse_subtitle,
    write_ass,
)

CHECKPOINT_FILENAME = ".checkpoint.json"


async def translate(
    subtitle_path: Path,
    *,
    target_lang: str,
    ai_config: AppConfig,
    glossary_path: Path | None = None,
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> TranslateResult:
    if not ai_config.ai_api_key:
        return TranslateResult(success=False, error="AI API key is not configured")

    out_dir = output_dir or subtitle_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / CHECKPOINT_FILENAME

    policy = resolve_http_proxy_policy(ai_config)
    client = AiClient(
        base_url=ai_config.ai_base_url,
        api_key=ai_config.ai_api_key,
        model=ai_config.ai_model,
        proxy=policy.proxy,
        trust_env=policy.trust_env,
    )
    client.max_retries = ai_config.ai_max_retries

    try:
        parsed_entries = parse_subtitle(subtitle_path)
        if not parsed_entries:
            return TranslateResult(success=False, error="No subtitle entries found")

        entries = parsed_entries
        if is_auto_generated(parsed_entries):
            entries = await client.segment_entries(
                parsed_entries,
                temperature=AI_TEMPERATURE_SEGMENTATION,
            )
            if not entries:
                return TranslateResult(
                    success=False, error="Segmentation produced no entries"
                )

        source_sample = _build_language_sample(entries)
        source_lang = await client.detect_language(source_sample)
        if _same_language(source_lang, target_lang):
            return TranslateResult(
                success=True,
                source_lang=source_lang,
                target_lang=target_lang,
                entry_count=len(entries),
                warnings=["Source language equals target language, skip translation"],
            )

        glossary_text = ""
        if glossary_path is not None:
            glossary_entries = load_glossary(glossary_path)
            glossary_text = format_glossary_for_prompt(glossary_entries)

        translated = await _translate_in_batches(
            client=client,
            entries=entries,
            target_lang=target_lang,
            glossary_text=glossary_text,
            batch_size=ai_config.ai_translate_batch_size,
            checkpoint_path=checkpoint_path,
            progress=progress,
        )
        proofread = await _proofread_in_batches(
            client=client,
            translated=translated,
            glossary_text=glossary_text,
            batch_size=ai_config.ai_proofread_batch_size,
            progress=progress,
        )

        ass_content = generate_bilingual_ass(
            proofread,
            font_name=Path(ai_config.font_file).stem,
        )
        output_path = out_dir / f"{subtitle_path.stem}.{target_lang}.ass"
        write_ass(ass_content, output_path)
        return TranslateResult(
            success=True,
            output_path=output_path,
            source_lang=source_lang,
            target_lang=target_lang,
            entry_count=len(entries),
            failed_count=0,
        )
    except Exception as exc:
        return TranslateResult(success=False, error=str(exc))
    finally:
        await client.close()


async def _translate_in_batches(
    *,
    client: AiClient,
    entries: list[SubtitleEntry],
    target_lang: str,
    glossary_text: str,
    batch_size: int,
    checkpoint_path: Path,
    progress: ProgressCallback | None,
) -> list[BilingualEntry]:
    total_batches = math.ceil(len(entries) / batch_size)
    translated: list[BilingualEntry] = []

    for batch_index in range(total_batches):
        start = batch_index * batch_size
        end = min(start + batch_size, len(entries))
        batch = entries[start:end]
        if progress is not None:
            progress.on_progress(
                batch_index + 1,
                total_batches,
                f"Translating batch {batch_index + 1}/{total_batches}",
                stage="translating",
            )

        outputs = await client.translate_batch(
            batch,
            target_lang=target_lang,
            glossary_text=glossary_text,
            temperature=AI_TEMPERATURE_DEFAULT,
        )
        bilingual_batch = [
            BilingualEntry(
                start_ms=entry.start_ms,
                end_ms=entry.end_ms,
                original=entry.text,
                translated=outputs[i],
            )
            for i, entry in enumerate(batch)
        ]
        translated.extend(bilingual_batch)
        _save_checkpoint(
            checkpoint_path,
            translated,
            {
                "translated_batches": batch_index + 1,
                "total_batches": total_batches,
            },
        )

    return translated


async def _proofread_in_batches(
    *,
    client: AiClient,
    translated: list[BilingualEntry],
    glossary_text: str,
    batch_size: int,
    progress: ProgressCallback | None,
) -> list[BilingualEntry]:
    total_batches = math.ceil(len(translated) / batch_size)
    output = [
        BilingualEntry(
            start_ms=entry.start_ms,
            end_ms=entry.end_ms,
            original=entry.original,
            translated=entry.translated,
        )
        for entry in translated
    ]

    for batch_index in range(total_batches):
        start = batch_index * batch_size
        end = min(start + batch_size, len(output))
        batch = output[start:end]
        context_start = max(0, start - batch_size)
        context_entries = output[context_start:start]
        if progress is not None:
            progress.on_progress(
                batch_index + 1,
                total_batches,
                f"Proofreading batch {batch_index + 1}/{total_batches}",
                stage="proofreading",
            )

        revised = await client.proofread_batch(
            batch,
            context_entries=context_entries,
            glossary_text=glossary_text,
            temperature=AI_TEMPERATURE_PROOFREADING,
        )
        for offset, text in enumerate(revised):
            output[start + offset].translated = text

    return output


def _build_language_sample(entries: list[SubtitleEntry]) -> str:
    sample_text = " ".join(entry.text for entry in entries)
    return sample_text[:AI_LANGUAGE_DETECT_SAMPLE_LENGTH]


def _same_language(source_lang: str, target_lang: str) -> bool:
    source = source_lang.strip().lower()
    target = target_lang.strip().lower()
    if not source or not target:
        return False
    return source == target or source == target.split("-")[0]


def _save_checkpoint(
    path: Path,
    entries: list[BilingualEntry],
    extra: dict[str, Any],
) -> None:
    payload = {
        "entries": [
            {
                "start_ms": entry.start_ms,
                "end_ms": entry.end_ms,
                "original": entry.original,
                "translated": entry.translated,
            }
            for entry in entries
        ],
        **extra,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
