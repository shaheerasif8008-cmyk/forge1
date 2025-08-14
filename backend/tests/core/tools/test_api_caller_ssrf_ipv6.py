from __future__ import annotations

import pytest

from app.core.tools.builtins.api_caller import APICaller


def test_api_caller_blocks_ipv6_ula(monkeypatch) -> None:
    tool = APICaller()
    # FC00::/7 example address; using literal with http scheme to trigger block via SSRF checks
    with pytest.raises(ValueError):
        tool.execute(method="GET", url="http://[fc00::1]/")


