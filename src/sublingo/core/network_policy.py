from __future__ import annotations

from dataclasses import dataclass

from sublingo.core.config import AppConfig
from sublingo.core.config import DEFAULT_PROXY_MODE
from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.config import PROXY_MODE_SYSTEM
from sublingo.core.config import normalize_proxy_mode


@dataclass(frozen=True)
class HttpProxyPolicy:
    proxy: str | None
    trust_env: bool


def resolve_http_proxy_policy(config: AppConfig) -> HttpProxyPolicy:
    mode = normalize_proxy_mode(config.proxy_mode)
    proxy_text = config.proxy.strip()
    if mode == PROXY_MODE_DISABLED:
        return HttpProxyPolicy(proxy=None, trust_env=False)
    if mode == PROXY_MODE_CUSTOM:
        return HttpProxyPolicy(proxy=proxy_text or None, trust_env=False)
    return HttpProxyPolicy(proxy=None, trust_env=True)


def resolve_download_proxy(config: AppConfig) -> str | None:
    mode = normalize_proxy_mode(config.proxy_mode)
    proxy_text = config.proxy.strip()
    if mode == PROXY_MODE_DISABLED:
        return ""
    if mode == PROXY_MODE_CUSTOM:
        return proxy_text or None
    return None


def resolve_http_proxy_from_values(
    proxy_mode: str | None,
    proxy: str | None,
) -> HttpProxyPolicy:
    config = AppConfig(
        proxy_mode=proxy_mode or DEFAULT_PROXY_MODE,
        proxy=proxy or "",
    )
    return resolve_http_proxy_policy(config)
