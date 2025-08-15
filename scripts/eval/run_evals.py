#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from evals.harness import EvalCase, run_suite  # noqa: E402


def main() -> int:
    # Define a small default suite; can be extended to read from files
    cases = [
        EvalCase(name="ceo_quarterly", task="Provide 3 initiatives to improve profitability next quarter.", rubric={"must_include": ["initiative", "profit"], "must_not": []}),
        EvalCase(name="testing_plan", task="Draft a concise test plan for the login flow.", rubric={"must_include": ["test"], "must_not": ["irrelevant"]}),
    ]
    data = {}
    try:
        import asyncio

        data = asyncio.run(run_suite(cases))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e)}))
        return 2
    out_dir = os.getenv("EVAL_OUT_DIR", os.path.join(os.getcwd(), "artifacts", f"evals_{os.getpid()}"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    avg = float(data.get("average", 0))
    threshold = float(os.getenv("EVAL_THRESHOLD", "0.7"))
    print(json.dumps({"average": avg, "threshold": threshold, "out": out_dir}))
    return 0 if avg >= threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())


