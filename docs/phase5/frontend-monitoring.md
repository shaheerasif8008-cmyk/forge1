### Phase 5: Frontend Monitoring Dashboard

Admin-only dashboard at `/admin/monitoring` visualizes core platform health and usage. It pulls from backend metrics and logs APIs.

### Features

- Summary KPIs: total tasks, avg duration, tokens, tool calls, errors
- Success ratio bar
- Token usage by day table
- Recent error logs (24h)
- Filters: tenant, date range (mapped to month granularity server-side)

### Data sources

- `/api/v1/metrics` (admin-only): aggregated usage stats and daily rollups
- `/api/v1/logs` (admin-only): recent audit/error logs with optional tenant filter

### Implementation

- Page: `frontend/src/pages/AdminMonitoringPage.tsx`
- Route: added to router as `/admin/monitoring` and guarded by session; page checks `user.role === 'admin'`
- Uses native tables and bars for simple visualizations; Chart library can be added later (Chart.js/Recharts) if needed

### Future Enhancements

- Swap tables/bars to charts (line chart for tokens over time; stacked bar for success/fail)
- Live updates via SSE/WebSocket for RPS and success ratios
- Tenant dropdown auto-populated from `/api/v1/tenants`


