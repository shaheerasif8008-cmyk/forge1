from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol, cast

try:
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    redis = None  # type: ignore

from ..config import settings
from ..flags.feature_flags import is_enabled
from ..logging_config import get_trace_id
from ...db.session import SessionLocal
from ...db.models import RouterMetric


logger = logging.getLogger(__name__)


class TaskTypeProtocol(Protocol):
    value: str


class LLMAdapterProtocol(Protocol):
    @property
    def model_name(self) -> str:  # e.g., openai-gpt-5 | claude-... | gemini-... | openrouter-gpt-4o
        ...

    @property
    def capabilities(self) -> list[Any]:  # list[TaskType]
        ...


class AdapterRegistryProtocol(Protocol):
    def get_adapters_for_task(self, task_type: Any) -> list[LLMAdapterProtocol]:  # TaskType
        ...

    def get_adapter(self, model_name: str) -> LLMAdapterProtocol | None:
        ...


def _provider_of(model_name: str) -> str:
    if model_name.startswith("openai-"):
        return "openai"
    if model_name.startswith("claude-"):
        return "claude"
    if model_name.startswith("gemini-"):
        return "gemini"
    if model_name.startswith("openrouter-"):
        return "openrouter"
    # heuristic for OpenRouter fully-qualified ids in adapter names
    if "/" in model_name:
        return "openrouter"
    return "unknown"


def _cost_cents_for_tokens(provider: str, tokens: int) -> int:
    # Approximate costs per 1k tokens (cents); configurable via env/settings
    per_1k_map = {
        "openai": int(getattr(settings, "openai_1k_token_cost_cents", 10)),
        "claude": int(getattr(settings, "claude_1k_token_cost_cents", 16)),
        "gemini": int(getattr(settings, "gemini_1k_token_cost_cents", 8)),
        "openrouter": int(getattr(settings, "openrouter_1k_token_cost_cents", 9)),
    }
    per_1k = per_1k_map.get(provider, 10)
    return int((tokens / 1000.0) * per_1k)


def _env_key_present(provider: str) -> bool:
    try:
        if provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        if provider == "claude":
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        if provider == "gemini":
            return bool(os.getenv("GOOGLE_AI_API_KEY"))
        if provider == "openrouter":
            return bool(os.getenv("OPENROUTER_API_KEY") or getattr(settings, "openrouter_api_key", None))
    except Exception:
        return False
    return False


@dataclass
class TenantPolicy:
    max_cents_per_day: int | None = None
    max_tokens_per_run: int | None = None


@dataclass
class RouterInputs:
    requested_model: str | None
    task_type: Any  # TaskType
    tenant_id: str
    employee_id: str | None
    tenant_policy: TenantPolicy
    latency_slo_ms: int | None
    prompt: str
    user_id: str | None
    function_name: str | None
    tools: list[dict[str, Any]] | None
    estimated_tokens: int | None = None


@dataclass
class RouterDecision:
    model_name: str
    provider: str
    reason: str


class CircuitBreaker:
    """Simple per-provider circuit breaker with optional Redis state sharing."""

    def __init__(self, *, threshold: int = 3, cooldown_secs: int = 60) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_secs
        self._states: dict[str, dict[str, Any]] = {}

    async def is_open(self, provider: str) -> bool:
        # Prefer Redis state if available (key: cb:llm:<provider>)
        key = f"cb:llm:{provider}"
        if redis is not None:
            try:
                client: redis.Redis = cast(redis.Redis, redis.from_url(settings.redis_url, decode_responses=True))
                state = await client.get(key)
                if state == "open":
                    return True
            except Exception:
                pass
        # Fallback to in-memory
        st = self._states.get(provider)
        if not st:
            return False
        if st["state"] == "OPEN" and (time.time() - st["last_trip"]) > self._cooldown:
            st["state"] = "HALF_OPEN"
        return st["state"] == "OPEN"

    async def record_success(self, provider: str) -> None:
        st = self._states.setdefault(provider, {"state": "CLOSED", "failures": 0, "last_trip": 0.0})
        st["failures"] = 0
        if st["state"] == "HALF_OPEN":
            st["state"] = "CLOSED"

    async def record_failure(self, provider: str) -> None:
        st = self._states.setdefault(provider, {"state": "CLOSED", "failures": 0, "last_trip": 0.0})
        st["failures"] += 1
        if st["state"] == "HALF_OPEN" or st["failures"] >= self._threshold:
            st["state"] = "OPEN"
            st["last_trip"] = time.time()
            if redis is not None:
                try:
                    client: redis.Redis = cast(redis.Redis, redis.from_url(settings.redis_url, decode_responses=True))
                    await client.setex(f"cb:llm:{provider}", self._cooldown, "open")
                except Exception:
                    pass


class PromptCache:
    def __init__(self, *, ttl_secs: int) -> None:
        self._ttl = max(0, int(ttl_secs))
        self._inmem: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _hash_key(model: str, function_name: str | None, user_id: str | None, prompt: str, tools: list[dict[str, Any]] | None) -> str:
        payload = {
            "model": model,
            "function": function_name or "",
            "user": user_id or "",
            "prompt": prompt,
            "tools": tools or [],
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"pc:{digest}"

    async def get(self, *, model: str, function_name: str | None, user_id: str | None, prompt: str, tools: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        if self._ttl <= 0:
            return None
        key = self._hash_key(model, function_name, user_id, prompt, tools)
        if redis is not None:
            try:
                client: redis.Redis = cast(redis.Redis, redis.from_url(settings.redis_url, decode_responses=True))
                val = await client.get(key)
                if val:
                    try:
                        return cast(dict[str, Any], json.loads(val))
                    except Exception:
                        return None
            except Exception:
                pass
        # Fallback in-memory (best-effort, no TTL eviction)
        return self._inmem.get(key)

    async def set(self, *, model: str, function_name: str | None, user_id: str | None, prompt: str, tools: list[dict[str, Any]] | None, response: dict[str, Any]) -> None:
        if self._ttl <= 0:
            return
        key = self._hash_key(model, function_name, user_id, prompt, tools)
        if redis is not None:
            try:
                client: redis.Redis = cast(redis.Redis, redis.from_url(settings.redis_url, decode_responses=True))
                await client.setex(key, self._ttl, json.dumps(response))
                return
            except Exception:
                pass
        self._inmem[key] = response


class ModelRouter:
    """Cost/latency-aware model router with prompt caching and feature-flag overrides."""

    def __init__(self, registry: AdapterRegistryProtocol) -> None:
        self._registry = registry
        self._cb = CircuitBreaker(
            threshold=int(getattr(settings, "circuit_breaker_threshold", 3)),
            cooldown_secs=int(getattr(settings, "circuit_breaker_cooldown_secs", 60)),
        )
        self._cache = PromptCache(ttl_secs=int(getattr(settings, "prompt_cache_ttl_secs", 300)))
        # Success similarity margin for cost optimizer (within margin of best expected success)
        try:
            self._similarity_margin = float(os.getenv("COST_OPTIMIZER_SUCCESS_MARGIN", "0.02"))
        except Exception:
            self._similarity_margin = 0.02

    async def maybe_get_cached(self, *, model: str, function_name: str | None, user_id: str | None, prompt: str, tools: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        return await self._cache.get(model=model, function_name=function_name, user_id=user_id, prompt=prompt, tools=tools)

    async def store_cache(self, *, model: str, function_name: str | None, user_id: str | None, prompt: str, tools: list[dict[str, Any]] | None, response: dict[str, Any]) -> None:
        await self._cache.set(model=model, function_name=function_name, user_id=user_id, prompt=prompt, tools=tools, response=response)

    async def record_provider_success(self, model_name: str) -> None:
        await self._cb.record_success(_provider_of(model_name))

    async def record_provider_failure(self, model_name: str) -> None:
        await self._cb.record_failure(_provider_of(model_name))

    def _apply_flag_overrides(self, tenant_id: str, candidates: list[str]) -> list[str]:
        # Force provider flags take precedence
        try:
            with SessionLocal() as db:
                for prov in ("openrouter", "openai", "claude", "gemini"):
                    if is_enabled(db, tenant_id, f"router.force_provider_{prov}", default=False):
                        return [c for c in candidates if _provider_of(c) == prov]
                # Disable flags filter out providers
                disabled: set[str] = set()
                for prov in ("openrouter", "openai", "claude", "gemini"):
                    if is_enabled(db, tenant_id, f"router.disable_provider_{prov}", default=False):
                        disabled.add(prov)
                if disabled:
                    return [c for c in candidates if _provider_of(c) not in disabled]
        except Exception:
            pass
        return candidates

    def _fallback_order(self) -> list[str]:
        raw = str(getattr(settings, "router_fallback_order", "openrouter,openai,claude,gemini")).strip()
        order = [s.strip() for s in raw.split(",") if s.strip()]
        if not order:
            order = ["openrouter", "openai", "claude", "gemini"]
        return order

    def _expected_success(self, tenant_id: str, task_type_value: str, provider: str) -> float | None:
        try:
            with SessionLocal() as db:
                row = (
                    db.query(RouterMetric.alpha, RouterMetric.beta)
                    .filter(
                        RouterMetric.tenant_id == tenant_id,
                        RouterMetric.task_type == task_type_value,
                        RouterMetric.model_name.like(f"{provider}%"),
                    )
                    .first()
                )
                if not row:
                    return None
                alpha, beta = int(row[0] or 1), int(row[1] or 1)
                return float(alpha) / float(alpha + beta)
        except Exception:
            return None

    def _score(self, provider: str, tokens: int, tenant_id: str, task_type_value: str, latency_slo_ms: int | None) -> float:
        # Lower is better
        cost = _cost_cents_for_tokens(provider, tokens)
        # Get p95 latency from RouterMetric when available
        p95_ms = None
        try:
            with SessionLocal() as db:
                row = (
                    db.query(RouterMetric.latency_p95)
                    .filter(RouterMetric.tenant_id == tenant_id, RouterMetric.task_type == task_type_value, RouterMetric.model_name.like(f"{provider}%"))
                    .first()
                )
                if row:
                    p95_ms = cast(int | None, row[0])
        except Exception:
            p95_ms = None
        # Normalize cost and latency roughly
        cost_norm = cost  # already in cents
        lat_norm = p95_ms if p95_ms is not None else 1000
        # SLA penalty if SLO provided
        slo_penalty = 0.0
        if latency_slo_ms is not None and lat_norm > latency_slo_ms:
            slo_penalty = (lat_norm - latency_slo_ms) * 0.5
        return float(cost_norm) + float(lat_norm) * 0.01 + slo_penalty

    async def select(self, inputs: RouterInputs) -> RouterDecision | None:
        adapters = self._registry.get_adapters_for_task(inputs.task_type)
        if not adapters:
            logger.warning("No adapters available for task type=%s", getattr(inputs.task_type, "value", str(inputs.task_type)))
            return None

        candidate_models = [a.model_name for a in adapters]
        # Apply availability by env keys
        candidate_models = [m for m in candidate_models if _env_key_present(_provider_of(m))]
        if not candidate_models:
            logger.warning("No providers available due to missing API keys")
            return None

        # Remove candidates with open circuit
        available: list[str] = []
        for m in candidate_models:
            prov = _provider_of(m)
            if not await self._cb.is_open(prov):
                available.append(m)

        if not available:
            logger.warning("All providers are circuit-open")
            return None

        # Requested model takes precedence if present and available
        if inputs.requested_model:
            for m in available:
                if inputs.requested_model in (m, m.replace("openrouter-", "")):
                    return RouterDecision(model_name=m, provider=_provider_of(m), reason="requested")

        # Flag overrides per tenant
        available = self._apply_flag_overrides(inputs.tenant_id, available)
        if not available:
            logger.warning("All candidates disabled by flags for tenant=%s", inputs.tenant_id)
            return None

        # Cost optimizer: filter to providers with expected success within margin of best
        task_type_value = getattr(inputs.task_type, "value", str(inputs.task_type))
        exp_success: dict[str, float] = {}
        best_exp = 0.0
        for m in available:
            prov = _provider_of(m)
            es = self._expected_success(inputs.tenant_id, task_type_value, prov)
            if es is None:
                # If unknown, assume baseline 0.5
                es = 0.5
            exp_success[m] = float(es)
            if es > best_exp:
                best_exp = float(es)
        # keep those within margin of best
        margin = max(0.0, float(self._similarity_margin))
        candidates = [m for m in available if exp_success.get(m, 0.5) >= (best_exp - margin)] or available

        # Scoring by cost/latency among candidates
        tokens = int(inputs.estimated_tokens or max(1, len(inputs.prompt) // 4))
        best_model = None
        best_score = float("inf")
        for m in candidates:
            prov = _provider_of(m)
            score = self._score(prov, tokens, inputs.tenant_id, task_type_value, inputs.latency_slo_ms)
            if score < best_score:
                best_model = m
                best_score = score

        # Fallback order tie-breaker
        if best_model is None:
            order = self._fallback_order()
            for prov in order:
                for m in available:
                    if _provider_of(m) == prov:
                        best_model = m
                        break
                if best_model:
                    break

        if best_model is None:
            return None

        return RouterDecision(model_name=best_model, provider=_provider_of(best_model), reason="scored")


