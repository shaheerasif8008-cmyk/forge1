### Client Portal: Premium, Self-Serve Experience

Scope delivered:

- Client Dashboard
  - Cards: active employees (placeholder), 24h runs, success %, p95 (derived), tokens, cost estimate
  - Charts (Recharts): usage over time with tasks and errors
  - Live activity feed: tenant-scoped SSE `/api/v1/ai-comms/events?token=`

- Onboarding Wizard
  - Steps: choose template → connect tools (guided toggles) → upload docs (URL) → name → test/go live
  - Uses APIs: `GET /marketplace/templates`, `POST /marketplace/templates/{key}/deploy`, `POST /rag/upload`
  - Save/resume can be layered via localStorage (future)

- In‑App Assistant
  - Chat panel using Central AI via `POST /ai/execute`, scoped to tenant
  - Can instruct to open a ticket using `POST /client/escalations`

- Branding / Dark Mode
  - Tenant branding endpoint `GET/POST /branding` (in-memory)
  - Frontend `ThemeProvider` applies colors and dark class

Backend endpoints:

- `GET /api/v1/client/metrics/summary?hours=24`
- `GET /api/v1/ai-comms/events?token=...` (SSE)
- `POST /api/v1/rag/upload` { items: [{ type, url|path, metadata? }] }
- `GET/POST /api/v1/branding`
- `POST /api/v1/client/escalations` { reason, employee_id? }

Frontend routes:

- `/dashboard` → ClientDashboardPage
- `/onboarding` → OnboardingWizardPage

Notes:

- SSE for tenant clients requires `token` query param since EventSource cannot set headers; the server verifies token and tenant match.
- Cost estimate is naive (tokens × rate). Replace with per-model pricing as telemetry matures.


