# Forge1 Frontend

A production-ready Next.js frontend for the Forge1 AI Employee Builder & Deployment Platform.

## Features

- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** with custom brand tokens
- **shadcn/ui** for beautiful, accessible components
- **TanStack Query** for server state management
- **Zustand** for client state management
- **SSE Support** with automatic reconnection
- **Authentication** with JWT (localStorage or httpOnly cookies)
- **Dark/Light Mode** with next-themes

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
# API Configuration (required)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Environment label shown in UI
NEXT_PUBLIC_ENV_LABEL=Development

# Authentication storage method
USE_LOCAL_STORAGE_AUTH=true
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run dev:proxy` - Start with development proxy (avoids CORS)
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── app/                 # Next.js App Router pages
├── components/          # Reusable UI components
│   └── ui/             # shadcn/ui components
├── hooks/              # Custom React hooks
├── lib/                # Utilities and configurations
├── providers/          # React context providers
└── types/              # TypeScript type definitions
```

## Authentication

The app supports two authentication modes:

1. **localStorage** (default): JWT stored in browser localStorage
2. **httpOnly cookies**: More secure, requires backend cookie support

Set `USE_LOCAL_STORAGE_AUTH=false` to use httpOnly cookies.

## Development Proxy

The optional development proxy (`npm run dev:proxy`) forwards `/api/*` requests to your backend API, avoiding CORS issues during local development.

## Production Build

```bash
npm run build
npm run start
```

The built application will be optimized for production deployment.

## Contributing

1. Follow TypeScript best practices
2. Use shadcn/ui components when possible
3. Maintain consistent styling with brand tokens
4. Test authentication flows thoroughly
5. Ensure accessibility standards are met

## License

See main project LICENSE file.