Testing Frontend

A lightweight Vite + React + TypeScript UI to drive the Testing App API.

## Env

Copy and edit `.env.example` as `.env.local`:

- VITE_TESTING_API_BASE_URL: e.g. https://testing-api.example.com
- VITE_ENV_LABEL: UI badge/label (optional)
- VITE_TESTING_ADMIN_JWT: optional admin JWT for protected endpoints; also supported via localStorage key `testing_admin_jwt`

## Auth Injection

If `VITE_TESTING_ADMIN_JWT` or localStorage `testing_admin_jwt` is present, requests include:
- Authorization: Bearer <jwt>
- X-Testing-Service-Key: <jwt>

## Scripts

- dev: vite
- build: tsc && vite build
- preview: vite preview

## Deploy (Azure Static Web Apps)

- Build
  - npm i
  - npm run build
- Deploy
  - Upload `dist/` with Azure Static Web Apps or via CI/CD
- Backend CORS
  - Add your SWA URL to Testing App `BACKEND_CORS_ORIGINS` if needed
