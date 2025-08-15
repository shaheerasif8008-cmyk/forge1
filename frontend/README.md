# Forge1 Frontend

A production-ready Next.js frontend for the Forge1 AI Employee Builder & Deployment Platform.

## Features

- **Next.js 15** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** with custom brand tokens
- **shadcn/ui** for beautiful, accessible components
- **TanStack Query** for server state management
- **SSE Support** with automatic reconnection
- **Authentication** with JWT (localStorage or httpOnly cookies)
- **Dark/Light Mode** support
- **Employee Management** with full CRUD operations
- **Real-time Operations Dashboard** with SSE
- **Usage & Billing Metrics** with Recharts

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your API URL
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Optional: Start with proxy (to avoid CORS):**
   ```bash
   npm run dev:proxy
   ```

## Environment Variables

Create a `.env.local` file with:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ENV_LABEL=Development
NEXT_PUBLIC_USE_LOCAL_STORAGE_AUTH=true
```

## Development

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript type checking

## Deployment

The app is configured for deployment to Azure Static Web Apps:

1. Build the app: `npm run build`
2. Deploy using Azure SWA CLI or GitHub Actions

## Architecture

- **Pages**: App Router with layouts and loading states
- **API Integration**: Strongly typed Axios client with interceptors
- **State Management**: TanStack Query for server state
- **Authentication**: JWT with refresh token support
- **Real-time**: SSE for live operations monitoring

## Project Structure

```
src/
├── app/                 # Next.js App Router pages
├── components/          # Reusable UI components
│   └── ui/             # shadcn/ui components
├── hooks/              # Custom React hooks
├── lib/                # Utilities and API client
│   ├── api/            # API client and types
│   ├── auth.tsx        # Authentication provider
│   ├── config.ts       # App configuration
│   └── utils.ts        # Utility functions
└── providers/          # React context providers
```