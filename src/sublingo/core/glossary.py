from __future__ import annotations

import csv
from pathlib import Path

GLOSSARY_HEADER_SOURCE = "source"
GLOSSARY_HEADER_TARGET = "target"


def load_glossary(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Glossary file not found: {path}")

    result: list[tuple[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return result

        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        source_key = field_map.get(GLOSSARY_HEADER_SOURCE)
        target_key = field_map.get(GLOSSARY_HEADER_TARGET)
        if source_key is None or target_key is None:
            return result

        for row in reader:
            source = (row.get(source_key) or "").strip()
            target = (row.get(target_key) or "").strip()
            if source and target:
                result.append((source, target))
    return result


def format_glossary_for_prompt(entries: list[tuple[str, str]]) -> str:
    if not entries:
        return ""
    lines = ["Glossary terms (use exact target terms where applicable):"]
    lines.extend(f"- {source} => {target}" for source, target in entries)
    return "\n".join(lines)
