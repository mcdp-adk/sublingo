from __future__ import annotations

from pathlib import Path
import tomllib


def test_httpx_dependency_enables_socks_extra() -> None:
    project_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text("utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dep.startswith("httpx[socks]") for dep in dependencies)
