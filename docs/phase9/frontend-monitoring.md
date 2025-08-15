## Multi-Region Active-Active (Backend Routing)

- Enable cost/health-based routing with env vars:
  - `REGION`, `MULTI_REGION_ROUTING_ENABLED`, `REGION_MAP`, `REGION_HEALTH_TTL_SECS`, `NON_CRITICAL_PATH_PREFIXES`
- Regions publish heartbeats via Redis: key `region:health:<region>` set to `1` with TTL.
- Backend middleware forwards non-critical requests to cheapest healthy region transparently.


