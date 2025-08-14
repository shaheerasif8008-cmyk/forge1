from __future__ import annotations

import json
import random
from typing import Any, Iterable, Optional

from redis import Redis
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import RouterMetric
from ..db.session import SessionLocal
from .policy import RouterPolicy
from .scorecard import ModelScorecard


class ThompsonRouter:
    """Context-aware model router using Thompson Sampling with policy constraints.

    Hot metrics are kept in Redis hashes and periodically persisted in Postgres
    `router_metrics`. If no cache exists, we hydrate from Postgres.
    """

    def __init__(self, tenant_id: str, task_type: str, *, rng: Optional[random.Random] = None) -> None:
        self.tenant_id = tenant_id
        self.task_type = task_type
        self.rng = rng or random.Random()
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def _redis_key(self) -> str:
        return f"router:scorecard:{self.tenant_id}:{self.task_type}"

    def _load_scorecards(self) -> dict[str, ModelScorecard]:
        key = self._redis_key()
        entries = self._redis.hgetall(key) or {}
        sc: dict[str, ModelScorecard] = {}
        if entries:
            for model_name, payload in entries.items():
                try:
                    data = json.loads(payload)
                    m = ModelScorecard.empty(model_name)
                    m.trials = int(data.get("trials", 0))
                    m.successes = int(data.get("successes", 0))
                    m.success_posterior.alpha = float(data.get("alpha", 1.0))
                    m.success_posterior.beta = float(data.get("beta", 1.0))
                    m.latency_stats.count = int(data.get("lat_n", 0))
                    m.latency_stats.mean = float(data.get("lat_mu", 0.0))
                    m.latency_stats.m2 = float(data.get("lat_m2", 0.0))
                    m.cost_stats.count = int(data.get("c_n", 0))
                    m.cost_stats.mean = float(data.get("c_mu", 0.0))
                    m.cost_stats.m2 = float(data.get("c_m2", 0.0))
                    sc[model_name] = m
                except Exception:
                    continue
            return sc
        # Fallback to Postgres hydration
        with SessionLocal() as db:
            try:
                RouterMetric.__table__.create(bind=db.get_bind(), checkfirst=True)
            except Exception:
                pass
            rows = (
                db.query(RouterMetric)
                .filter(RouterMetric.tenant_id == self.tenant_id, RouterMetric.task_type == self.task_type)
                .all()
            )
            for r in rows:
                m = ModelScorecard.empty(r.model_name)
                m.trials = int(r.trials or 0)
                m.successes = int(r.successes or 0)
                m.success_posterior.alpha = float(r.alpha or 1)
                m.success_posterior.beta = float(r.beta or 1)
                # approximate with available p95/mean for hot start
                if r.latency_mu is not None:
                    m.latency_stats.count = max(1, int(r.trials or 1))
                    m.latency_stats.mean = float(r.latency_mu)
                if r.cost_mu is not None:
                    m.cost_stats.count = max(1, int(r.trials or 1))
                    m.cost_stats.mean = float(r.cost_mu)
                sc[r.model_name] = m
            return sc

    def _persist_hot(self, sc: dict[str, ModelScorecard]) -> None:
        key = self._redis_key()
        pipe = self._redis.pipeline()
        for name, m in sc.items():
            payload = json.dumps(
                {
                    "trials": m.trials,
                    "successes": m.successes,
                    "alpha": m.success_posterior.alpha,
                    "beta": m.success_posterior.beta,
                    "lat_n": m.latency_stats.count,
                    "lat_mu": m.latency_stats.mean,
                    "lat_m2": m.latency_stats.m2,
                    "c_n": m.cost_stats.count,
                    "c_mu": m.cost_stats.mean,
                    "c_m2": m.cost_stats.m2,
                }
            )
            pipe.hset(key, name, payload)
        pipe.expire(key, 3600)
        pipe.execute()

    def route(self, *, models: Iterable[str], policy: RouterPolicy) -> dict[str, Any]:
        scorecards = self._load_scorecards()
        candidates = [m for m in models if policy.is_allowed(m)]
        if not candidates:
            candidates = list(models)
        # Thompson sample success
        best_model = None
        best_sample = -1.0
        for m in candidates:
            sc = scorecards.get(m) or ModelScorecard.empty(m)
            sample = sc.success_posterior.sample(self.rng)
            # Soft constraints: penalize if hot p95 exceeds SLO or cost too high
            if policy.max_latency_ms and sc.latency_stats.count:
                if sc.latency_stats.approx_p95() > policy.max_latency_ms:
                    sample *= 0.8
            if policy.max_cost_per_task_cents and sc.cost_stats.count:
                if sc.cost_stats.approx_p95() > policy.max_cost_per_task_cents:
                    sample *= 0.8
            if sample > best_sample:
                best_sample = sample
                best_model = m
        best_model = best_model or (candidates[0] if candidates else None)
        return {"model": best_model, "params": {}}

    def record_outcome(
        self,
        *,
        model_name: str,
        success: bool,
        latency_ms: Optional[float],
        cost_cents: Optional[float],
    ) -> None:
        sc = self._load_scorecards()
        entry = sc.get(model_name) or ModelScorecard.empty(model_name)
        entry.update(success=success, latency_ms=latency_ms, cost_cents=cost_cents)
        sc[model_name] = entry
        self._persist_hot(sc)
        # Best-effort durable upsert
        try:
            with SessionLocal() as db:
                self._upsert_db(db, entry)
        except Exception:
            pass

    def _upsert_db(self, db: Session, m: ModelScorecard) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        RouterMetric.__table__.create(bind=db.get_bind(), checkfirst=True)
        # Approximate mu/sigma and p95 from current stats
        lat_mu = int(m.latency_stats.mean) if m.latency_stats.count else None
        lat_p95 = int(m.latency_stats.approx_p95()) if m.latency_stats.count else None
        c_mu = int(m.cost_stats.mean) if m.cost_stats.count else None
        c_p95 = int(m.cost_stats.approx_p95()) if m.cost_stats.count else None

        stmt = pg_insert(RouterMetric).values(
            tenant_id=self.tenant_id,
            task_type=self.task_type,
            model_name=m.model_name,
            alpha=int(m.success_posterior.alpha),
            beta=int(m.success_posterior.beta),
            latency_mu=lat_mu,
            latency_p95=lat_p95,
            cost_mu=c_mu,
            cost_p95=c_p95,
            trials=m.trials,
            successes=m.successes,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[RouterMetric.tenant_id, RouterMetric.task_type, RouterMetric.model_name],
            set_={
                "alpha": int(m.success_posterior.alpha),
                "beta": int(m.success_posterior.beta),
                "latency_mu": lat_mu,
                "latency_p95": lat_p95,
                "cost_mu": c_mu,
                "cost_p95": c_p95,
                "trials": m.trials,
                "successes": m.successes,
                "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            },
        )
        db.execute(stmt)
        db.commit()


