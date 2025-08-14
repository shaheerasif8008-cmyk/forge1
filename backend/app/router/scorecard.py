from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Optional


@dataclass
class PosteriorBeta:
    alpha: float = 1.0
    beta: float = 1.0

    def sample(self, rng) -> float:  # rng: random.Random
        # Use rng.betavariate for deterministic sampling in tests
        return rng.betavariate(self.alpha, self.beta)

    def update(self, success: bool) -> None:
        if success:
            self.alpha += 1.0
        else:
            self.beta += 1.0


@dataclass
class RollingGaussian:
    # Welford's algorithm state for online mean/variance
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self) -> float:
        return (self.m2 / (self.count - 1)) if self.count > 1 else 0.0

    @property
    def sigma(self) -> float:
        return sqrt(max(0.0, self.variance))

    def approx_p95(self) -> float:
        # For normal, p95 ~ mu + 1.645*sigma
        return float(self.mean + 1.645 * self.sigma)


@dataclass
class ModelScorecard:
    model_name: str
    success_posterior: PosteriorBeta
    latency_stats: RollingGaussian
    cost_stats: RollingGaussian
    trials: int = 0
    successes: int = 0

    @classmethod
    def empty(cls, model_name: str) -> "ModelScorecard":
        return cls(
            model_name=model_name,
            success_posterior=PosteriorBeta(),
            latency_stats=RollingGaussian(),
            cost_stats=RollingGaussian(),
        )

    def update(self, *, success: bool, latency_ms: Optional[float], cost_cents: Optional[float]) -> None:
        self.trials += 1
        if success:
            self.successes += 1
        self.success_posterior.update(success)
        if latency_ms is not None:
            self.latency_stats.update(float(latency_ms))
        if cost_cents is not None:
            self.cost_stats.update(float(cost_cents))


