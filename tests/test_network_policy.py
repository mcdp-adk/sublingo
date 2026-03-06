from __future__ import annotations

from sublingo.core.config import AppConfig
from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.config import PROXY_MODE_SYSTEM
from sublingo.core.network_policy import resolve_download_proxy
from sublingo.core.network_policy import resolve_http_proxy_from_values
from sublingo.core.network_policy import resolve_http_proxy_policy


def test_resolve_http_proxy_policy_system_mode() -> None:
    config = AppConfig(proxy_mode=PROXY_MODE_SYSTEM, proxy="")
    policy = resolve_http_proxy_policy(config)

    assert policy.proxy is None
    assert policy.trust_env is True


def test_resolve_http_proxy_policy_custom_mode() -> None:
    config = AppConfig(proxy_mode=PROXY_MODE_CUSTOM, proxy="http://127.0.0.1:7890")
    policy = resolve_http_proxy_policy(config)

    assert policy.proxy == "http://127.0.0.1:7890"
    assert policy.trust_env is False


def test_resolve_http_proxy_policy_disabled_mode() -> None:
    config = AppConfig(proxy_mode=PROXY_MODE_DISABLED, proxy="http://127.0.0.1:7890")
    policy = resolve_http_proxy_policy(config)

    assert policy.proxy is None
    assert policy.trust_env is False


def test_resolve_download_proxy_for_all_modes() -> None:
    assert (
        resolve_download_proxy(AppConfig(proxy_mode=PROXY_MODE_SYSTEM, proxy=""))
        is None
    )
    assert (
        resolve_download_proxy(
            AppConfig(proxy_mode=PROXY_MODE_CUSTOM, proxy="http://127.0.0.1:7890")
        )
        == "http://127.0.0.1:7890"
    )
    assert (
        resolve_download_proxy(
            AppConfig(proxy_mode=PROXY_MODE_DISABLED, proxy="http://127.0.0.1:7890")
        )
        == ""
    )


def test_resolve_http_proxy_from_values_uses_normalization() -> None:
    policy = resolve_http_proxy_from_values("CUSTOM", "http://127.0.0.1:7890")

    assert policy.proxy == "http://127.0.0.1:7890"
    assert policy.trust_env is False
