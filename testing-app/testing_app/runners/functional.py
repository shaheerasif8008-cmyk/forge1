from __future__ import annotations

from typing import Any
import os

import httpx

from testing_app.services.artifacts import save_json_artifact


def execute_functional_suite(run_id: int, target_api_url: str, scenarios: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
	client = httpx.Client(timeout=10.0)
	findings: list[dict[str, Any]] = []
	stats = {
		"total": 0,
		"passed": 0,
		"failed": 0,
		"latency_ms_sum": 0.0,
	}
	case_results: list[dict[str, Any]] = []
	for sc in scenarios:
		stats["total"] += 1
		try:
			method = sc.get("method", "GET").upper()
			path = sc.get("path", "/health")
			url = f"{target_api_url.rstrip('/')}{path}"
			payload = sc.get("payload")
			headers = dict(sc.get("headers", {}))
			# Optional admin Authorization header from env when not provided in scenario
			if "Authorization" not in {k.title(): v for k, v in headers.items()}:
				jwt = os.getenv("TESTING_ADMIN_JWT")
				if jwt:
					headers["Authorization"] = f"Bearer {jwt}"
			r = client.request(method, url, json=payload, headers=headers)
			passed = True
			asserts = sc.get("asserts") or {}
			# Flexible status assertions: int or list (may include sentinel 'SKIP_IF_404')
			if "status" in asserts:
				want = asserts["status"]
				allowed: list[int] = []
				skip_if_404 = False
				if isinstance(want, int):
					allowed = [int(want)]
				elif isinstance(want, list):
					for item in want:
						if isinstance(item, int):
							allowed.append(int(item))
						elif isinstance(item, str) and item.upper() == "SKIP_IF_404":
							skip_if_404 = True
				if r.status_code not in allowed:
					if r.status_code == 404 and skip_if_404:
						# Mark as skipped (not failed)
						case_results.append({"path": path, "status": r.status_code, "passed": True, "skipped": True})
						continue
					passed = False
			if "contains" in asserts:
				if asserts["contains"] not in r.text:
					passed = False
			# Optional JSON key/value assertions
			if "json_contains" in asserts:
				try:
					js = r.json()
					for k, v in (asserts["json_contains"] or {}).items():
						if js.get(k) != v:
							passed = False
							break
				except Exception:
					passed = False
			if "json_has_keys" in asserts:
				try:
					js = r.json()
					req_keys = list(asserts["json_has_keys"] or [])
					for k in req_keys:
						if k not in js:
							passed = False
							break
				except Exception:
					passed = False
			if not passed:
				findings.append(
					{
						"severity": "medium",
						"area": sc.get("name", path),
						"message": f"Assertion failed for {path}",
						"trace_id": None,
						"suggested_fix": "Check endpoint behavior and assertions",
					}
				)
				stats["failed"] += 1
			else:
				stats["passed"] += 1
			case_results.append({"path": path, "status": r.status_code, "passed": passed})
		except Exception as ex:
			findings.append(
				{
					"severity": "high",
					"area": sc.get("name", sc.get("path", "")),
					"message": f"Exception: {ex}",
					"trace_id": None,
					"suggested_fix": "Check network connectivity and target URL",
				}
			)
			stats["failed"] += 1
	save_json_artifact(run_id, "functional_results", {"cases": case_results})
	return stats, findings


