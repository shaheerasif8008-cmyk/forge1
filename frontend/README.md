# Forge 1 Frontend

A modern React TypeScript frontend for the Forge 1 AI orchestration platform, built with Vite, Tailwind CSS, and React Router.

## Features

- **React 19**: Latest React with modern hooks and features
- **TypeScript**: Full type safety and IntelliSense support
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework for rapid UI development
- **React Router**: Client-side routing with navigation
- **Responsive Design**: Mobile-first responsive layout
- **Modern UI**: Clean, professional interface design

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
   # Create .env file
   echo "VITE_API_URL=http://localhost:8000" > .env
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Project Structure

```
frontend/
├── src/
│   ├── pages/         # Page components
│   │   ├── LoginPage.tsx      # Login form
│   │   └── DashboardPage.tsx  # Main dashboard
│   ├── assets/        # Static assets
│   ├── App.tsx        # Main app component
│   ├── main.tsx       # App entry point
│   └── config.ts      # Configuration
├── public/            # Public assets
├── tailwind.config.js # Tailwind configuration
├── vite.config.ts     # Vite configuration
└── package.json       # Dependencies and scripts
```

### Adding New Pages

1. **Create page component:**
   ```tsx
   // src/pages/NewPage.tsx
   export default function NewPage() {
     return (
       <div className="max-w-4xl mx-auto p-6">
         <h1 className="text-3xl font-semibold mb-6">New Page</h1>
         {/* Page content */}
       </div>
     );
   }
   ```

2. **Add route in App.tsx:**
   ```tsx
   import NewPage from "./pages/NewPage";
   
   // In Routes component
   <Route path="/new-page" element={<NewPage />} />
   ```

### Styling

The project uses Tailwind CSS for styling. Key design patterns:

- **Layout**: Use `max-w-4xl mx-auto p-6` for page containers
- **Cards**: Use `bg-white rounded-lg shadow p-6` for content panels
- **Buttons**: Use `bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors`
- **Forms**: Use consistent input styling with focus states

### API Integration

The frontend communicates with the backend API:

- **Base URL**: Configured via `VITE_API_URL` environment variable
- **Authentication**: JWT tokens stored in localStorage
- **Error Handling**: Graceful fallbacks for API failures

## Building for Production

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Preview the build:**
   ```bash
   npm run preview
   ```

3. **Deploy the `dist/` folder** to your hosting provider

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `npm run lint`
5. Submit a pull request

## License

This project is licensed under the MIT License.
