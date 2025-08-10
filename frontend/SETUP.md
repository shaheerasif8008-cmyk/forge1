# Forge 1 Frontend Setup

React + TypeScript + Vite + Tailwind CSS frontend application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
# Create .env file in frontend directory
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. Start development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Features

- **Login Page**: Email/password authentication with JWT storage
- **Dashboard**: 
  - Backend health monitoring
  - User profile information
  - Create Employee button (placeholder)

## Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Run ESLint
- `npm run preview` - Preview production build

## Tailwind CSS

Tailwind CSS is already configured and ready to use. The configuration file is `tailwind.config.js` and the base styles are imported in `src/index.css`.
