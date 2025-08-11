# Forge 1 Frontend Setup

This is the React + TypeScript + Tailwind CSS frontend for the Forge 1 project.

## Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running (see backend README)

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment:**
   ```bash
   cp env.example .env
   # Edit .env with your API URL
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open browser:**
   Navigate to `http://localhost:5173`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ErrorBoundary.tsx
│   ├── LoadingSpinner.tsx
│   └── SessionManager.tsx
├── pages/              # Page components
│   ├── LoginPage.tsx
│   └── DashboardPage.tsx
├── config.ts           # Configuration and environment
├── App.tsx            # Main app component
└── main.tsx           # Entry point
```

## Features

- **Authentication**: JWT-based login/logout
- **Session Management**: Automatic token handling and user state
- **AI Task Execution**: Interface for running AI tasks
- **Real-time Health Monitoring**: Backend service status
- **Responsive Design**: Mobile-first Tailwind CSS
- **Error Handling**: Comprehensive error boundaries and user feedback
- **Type Safety**: Full TypeScript coverage

## Configuration

### Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)
- `VITE_ENVIRONMENT`: Environment name (default: development)
- `VITE_APP_VERSION`: App version (default: 1.0.0)

### Feature Flags

- `VITE_FEATURE_AI_TASKS`: Enable AI task execution
- `VITE_FEATURE_SESSION_MANAGEMENT`: Enable session management
- `VITE_FEATURE_ERROR_BOUNDARY`: Enable error boundaries

## Development

### Adding New Components

1. Create component in `src/components/`
2. Export from component file
3. Import and use in pages

### Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Update navigation if needed

### Styling

- Use Tailwind CSS classes
- Follow mobile-first responsive design
- Maintain consistent spacing and colors

## Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

## Building for Production

```bash
# Build the app
npm run build

# Preview production build
npm run preview

# The built files will be in the `dist/` directory
```

## Deployment

### Static Hosting (Netlify, Vercel, etc.)

1. Build the app: `npm run build`
2. Deploy the `dist/` directory
3. Set environment variables in hosting platform

### Docker

```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check backend is running
   - Verify `VITE_API_URL` in `.env`
   - Check CORS configuration in backend

2. **Build Errors**
   - Clear `node_modules` and reinstall
   - Check TypeScript errors
   - Verify all imports are correct

3. **Authentication Issues**
   - Check JWT token in localStorage
   - Verify backend auth endpoints
   - Check token expiration

### Debug Mode

Enable debug logging by setting `VITE_ENVIRONMENT=development` in `.env`.

## Contributing

1. Follow TypeScript best practices
2. Use functional components with hooks
3. Maintain consistent code style
4. Add proper error handling
5. Test thoroughly before submitting

## License

See main project LICENSE file.
