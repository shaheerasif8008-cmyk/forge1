from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from testing_app.core.config import settings


@dataclass
class ChaosHandle:
    proxy_name: str | None
    listen_host: str | None
    listen_port: int | None
    proxy_url: str | None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _parse_host_port(target_api_url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    u = urlparse(target_api_url)
    host = u.hostname or "localhost"
    port = u.port or (443 if u.scheme == "https" else 80)
    return host, port


def _public_host_for_proxy() -> str:
    # Allow override if containers need a different hostname to reach the proxy
    import os

    return os.getenv("TESTING_TOXIPROXY_PUBLIC_HOST") or (httpx.URL(settings.toxiproxy_url or "http://localhost:8474").host or "localhost")


def start_experiment(target_api_url: str, profile: dict[str, Any]) -> tuple[dict[str, Any], ChaosHandle]:
    # Simulation mode for CI
    if profile.get("simulate"):
        handle = ChaosHandle(proxy_name=None, listen_host=None, listen_port=None, proxy_url=target_api_url)
        return ({"enabled": True, "applied": [{"type": "simulate"}], "proxy_url": target_api_url}, handle)

    toxiproxy = settings.toxiproxy_url
    if not toxiproxy:
        return ({"enabled": False}, ChaosHandle(None, None, None, None))

    host, port = _parse_host_port(target_api_url)
    listen_port = int(profile.get("listen_port", 18888))
    proxy_name = profile.get("proxy_name") or f"forge1_{host}_{port}"
    applied: list[dict[str, Any]] = []
    listen_addr = f"0.0.0.0:{listen_port}"
    upstream = f"{host}:{port}"
    try:
        with httpx.Client(timeout=5.0) as client:
            # Ensure proxy exists
            r = client.post(
                f"{toxiproxy.rstrip('/')}/proxies",
                json={"name": proxy_name, "listen": listen_addr, "upstream": upstream},
            )
            if r.status_code == 409:
                # Already exists; update listen/upstream
                client.delete(f"{toxiproxy.rstrip('/')}/proxies/{proxy_name}")
                client.post(f"{toxiproxy.rstrip('/')}/proxies", json={"name": proxy_name, "listen": listen_addr, "upstream": upstream})
            # Latency toxic
            latency_ms = int(_clamp(float(profile.get("latency_ms", 300.0)), 200.0, 800.0))
            jitter_ms = int(_clamp(float(profile.get("jitter_ms", 50.0)), 0.0, 400.0))
            loss_pct = float(_clamp(float(profile.get("loss_pct", 1.0)), 0.0, 5.0))
            bw_kbps = int(_clamp(float(profile.get("bandwidth_kbps", 0.0)), 0.0, 100000.0))
            tox_url = f"{toxiproxy.rstrip('/')}/proxies/{proxy_name}/toxics"
            def _add(toxic_type: str, attributes: dict[str, Any]) -> None:
                try:
                    rr = client.post(tox_url, json={"type": toxic_type, "attributes": attributes})
                    if rr.status_code in (200, 201):
                        applied.append({"toxic": toxic_type, "attributes": attributes})
                except Exception:
                    pass
            _add("latency", {"latency": latency_ms, "jitter": jitter_ms})
            if loss_pct > 0:
                _add("limit_data", {"bytes_per_second": max(1, int(bw_kbps * 1024))} if bw_kbps else {"bytes_per_second": 0})
                _add("loss", {"percentage": loss_pct})
    except Exception:
        return ({"enabled": False}, ChaosHandle(None, None, None, None))

    public_host = _public_host_for_proxy()
    proxy_url = f"http://{public_host}:{listen_port}"
    return ({"enabled": True, "applied": applied, "proxy_url": proxy_url, "proxy_name": proxy_name, "listen_port": listen_port}, ChaosHandle(proxy_name, public_host, listen_port, proxy_url))


def stop_experiment(handle: ChaosHandle) -> dict[str, Any]:
    if not handle.proxy_name or not settings.toxiproxy_url:
        return {"stopped": True}
    try:
        with httpx.Client(timeout=5.0) as client:
            client.delete(f"{settings.toxiproxy_url.rstrip('/')}/proxies/{handle.proxy_name}")
    except Exception:
        pass
    return {"stopped": True}


def run_chaos_profile(profile: dict[str, Any]) -> dict[str, Any]:
    # Retained for backward compatibility; prefer start_experiment/stop_experiment
    toxiproxy = settings.toxiproxy_url
    if not toxiproxy:
        return {"enabled": False}
    rules = profile.get("rules", []) if isinstance(profile, dict) else []
    applied = []
    with httpx.Client(timeout=5.0) as client:
        for rule in rules:
            try:
                proxy = rule.get("proxy", "forge1")
                toxic = rule.get("type", "latency")
                attributes = rule.get("attributes", {"latency": 100})
                url = f"{toxiproxy.rstrip('/')}/proxies/{proxy}/toxics"
                r = client.post(url, json={"name": toxic, "type": toxic, "attributes": attributes})
                if r.status_code in (200, 201):
                    applied.append({"proxy": proxy, "toxic": toxic})
            except Exception:
                continue
    return {"enabled": True, "applied": applied}


