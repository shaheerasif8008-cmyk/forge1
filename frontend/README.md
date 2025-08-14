# Forge1 Frontend

A modern, enterprise-grade React + TypeScript + Tailwind CSS frontend for the Forge1 AI Employee Builder & Deployment platform.

## Features

### Client Portal
- **Dashboard**: Overview of AI employees, performance stats, and billing information
- **Employee Management**: Start/stop, logs, retraining, and performance monitoring
- **Employee Builder**: Step-by-step wizard for creating AI employees
- **Billing & Subscription**: Stripe integration for subscription management
- **Settings & Profile**: User preferences and account configuration

### Testing App
- **Test Suite Selector**: Predefined test configurations for stress testing
- **Live Test Monitor**: Real-time logs and test execution monitoring
- **Performance Dashboard**: Comprehensive charts and metrics analysis
- **Result Reports**: HTML/PDF test reports with detailed analysis

### Technical Features
- **Authentication**: JWT-based authentication with protected routes
- **Real-time Updates**: SSE/WebSocket integration for live data
- **Responsive Design**: Mobile-first, fully responsive interface
- **Dark/Light Mode**: Theme switching with system preference detection
- **State Management**: Zustand for efficient state management
- **Error Handling**: Comprehensive error boundaries and toast notifications
- **TypeScript**: Full type safety and IntelliSense support

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4 with shadcn/ui components
- **State Management**: Zustand
- **Charts**: Recharts for data visualization
- **Icons**: Lucide React
- **Authentication**: JWT with secure token storage
- **HTTP Client**: Axios for API communication
- **Notifications**: React Hot Toast
- **UI Components**: Radix UI primitives with custom styling

## Prerequisites

- Node.js 18+ 
- npm 9+ or yarn 1.22+
- Git

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Environment Configuration

The application supports multiple environments with different configuration files:

### Development (.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io
NEXT_PUBLIC_ENV_LABEL=Development
USE_LOCAL_STORAGE_AUTH=true
NEXT_PUBLIC_DEBUG_MODE=true
```

### Staging (.env.staging)
```bash
NEXT_PUBLIC_API_BASE_URL=https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io
NEXT_PUBLIC_ENV_LABEL=Staging
USE_LOCAL_STORAGE_AUTH=false
NEXT_PUBLIC_DEBUG_MODE=false
```

### Production (.env.production)
```bash
NEXT_PUBLIC_API_BASE_URL=https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io
NEXT_PUBLIC_ENV_LABEL=Production
USE_LOCAL_STORAGE_AUTH=false
NEXT_PUBLIC_DEBUG_MODE=false
```

## Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run build:staging` - Build for staging environment
- `npm run build:production` - Build for production environment
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── dashboard/         # Client Portal Dashboard
│   ├── employees/         # AI Employee Management
│   ├── builder/           # Employee Builder Wizard
│   ├── billing/           # Billing & Subscription
│   ├── settings/          # User Settings & Profile
│   └── testing/           # Testing App
│       ├── suites/        # Test Suite Selector
│       ├── monitor/       # Live Test Monitor
│       ├── performance/   # Performance Dashboard
│       └── reports/       # Test Reports
├── components/            # Reusable UI components
│   ├── ui/               # shadcn/ui components
│   ├── main-nav.tsx      # Main navigation
│   ├── protected-route.tsx # Route protection
│   └── authenticated-layout.tsx # Layout wrapper
├── lib/                  # Utility libraries
│   ├── api.ts            # API client
│   ├── auth.tsx          # Authentication context
│   ├── config.ts         # Environment configuration
│   └── utils.ts          # Utility functions
├── providers/            # React context providers
│   ├── theme-provider.tsx # Theme management
│   └── query-provider.tsx # React Query provider
└── hooks/                # Custom React hooks
```

## Development

### Adding New Pages

1. Create a new directory in `src/app/`
2. Add a `page.tsx` file
3. Use the `AuthenticatedLayout` component for protected pages
4. Follow the existing component patterns

### Adding New Components

1. Create components in `src/components/`
2. Use TypeScript interfaces for props
3. Follow the shadcn/ui component patterns
4. Add proper accessibility attributes

### Styling Guidelines

- Use Tailwind CSS utility classes
- Follow the design system in `tailwind.config.ts`
- Use CSS variables for theme colors
- Ensure responsive design for all components

### State Management

- Use Zustand for global state
- Use React state for component-local state
- Use React Query for server state management
- Follow the established patterns in existing stores

## API Integration

The frontend communicates with the Forge1 backend API:

- **Base URL**: `https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io`
- **Authentication**: JWT tokens in Authorization header
- **Endpoints**: RESTful API with standard HTTP methods
- **Real-time**: SSE for live updates (under testing)

### API Client

The `src/lib/api.ts` file contains the API client with:
- Automatic token management
- Request/response interceptors
- Error handling
- Type-safe API calls

## Authentication

The application uses JWT-based authentication:

- **Login**: Email/password authentication
- **Token Storage**: Secure localStorage or httpOnly cookies
- **Protected Routes**: Automatic redirect to login
- **Token Refresh**: Automatic token renewal

## Deployment

### Azure Static Web Apps

The frontend is designed for deployment to Azure Static Web Apps:

1. **Build the application**
   ```bash
   npm run build:production
   ```

2. **Deploy to Azure**
   - Connect your GitHub repository
   - Configure build settings
   - Set environment variables

3. **Environment Variables**
   - `NEXT_PUBLIC_API_BASE_URL`
   - `NEXT_PUBLIC_ENV_LABEL`
   - Other feature flags as needed

### Build Configuration

The build process:
- Optimizes for production
- Generates static assets
- Includes environment-specific configuration
- Optimizes bundle size

## Testing

### Manual Testing

1. **Client Portal Flow**
   - Login → Dashboard → Employees → Builder → Billing → Settings

2. **Testing App Flow**
   - Test Suites → Live Monitor → Performance → Reports

3. **Cross-browser Testing**
   - Chrome, Firefox, Safari, Edge
   - Mobile responsive testing

### Automated Testing

- **TypeScript**: `npm run type-check`
- **Linting**: `npm run lint`
- **Build**: `npm run build`

## Performance

### Optimization Features

- **Code Splitting**: Automatic route-based code splitting
- **Image Optimization**: Next.js Image component
- **Bundle Analysis**: Built-in bundle analyzer
- **Lazy Loading**: Component and route lazy loading

### Monitoring

- **Performance Metrics**: Core Web Vitals
- **Error Tracking**: Comprehensive error boundaries
- **Analytics**: Optional analytics integration

## Security

### Security Features

- **HTTPS Only**: Production deployment enforces HTTPS
- **CSP Headers**: Content Security Policy
- **XSS Protection**: React's built-in XSS protection
- **CSRF Protection**: Token-based CSRF protection
- **Input Validation**: Client-side and server-side validation

### Best Practices

- Never expose sensitive data in client-side code
- Use environment variables for configuration
- Implement proper error handling
- Validate all user inputs
- Use HTTPS in production

## Troubleshooting

### Common Issues

1. **Build Errors**
   - Check TypeScript errors: `npm run type-check`
   - Verify environment variables
   - Clear `.next` directory

2. **Authentication Issues**
   - Check token expiration
   - Verify API endpoint configuration
   - Check browser console for errors

3. **Styling Issues**
   - Verify Tailwind CSS configuration
   - Check component class names
   - Ensure proper CSS imports

### Debug Mode

Enable debug mode in development:
```bash
NEXT_PUBLIC_DEBUG_MODE=true
```

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Update documentation for API changes
4. Test thoroughly before submitting PRs
5. Follow the commit message conventions

## License

This project is proprietary software. All rights reserved.

## Support

For technical support or questions:
- Check the documentation
- Review existing issues
- Contact the development team