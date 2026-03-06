from __future__ import annotations

import re
from pathlib import Path

WINDOWS_DRIVE_ABS_PATTERN = re.compile(r"^[A-Za-z]:[\\/].+")


def is_windows_absolute_path(value: str) -> bool:
    raw = value.strip()
    return bool(raw.startswith("\\\\") or WINDOWS_DRIVE_ABS_PATTERN.match(raw))


def resolve_user_path(value: str, base_dir: Path) -> Path:
    raw = value.strip()
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate.resolve()
    if is_windows_absolute_path(raw):
        return Path(raw)
    return (base_dir / candidate).resolve()
