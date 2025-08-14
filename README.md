# Forge 1 - AI Orchestration Platform

A modern, full-stack AI orchestration platform built with FastAPI, React, and TypeScript. Forge 1 provides intelligent task routing, session management, and a beautiful user interface for AI-powered applications.

## 🚀 Features

- **AI Task Orchestration**: Intelligent routing of tasks to appropriate AI models
- **Session Management**: Redis-based session storage with automatic cleanup
- **Authentication**: JWT-based authentication system
- **Real-time Health Monitoring**: Comprehensive backend service monitoring
- **Modern Frontend**: React + TypeScript + Tailwind CSS with responsive design
- **Error Handling**: Robust error boundaries and user feedback
- **Docker Support**: Containerized development and deployment
- **CI/CD**: GitHub Actions for automated testing and deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Infrastructure │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Docker)      │
│                 │    │                 │    │                 │
│ • Dashboard     │    │ • AI Orchestrator│   │ • PostgreSQL    │
│ • Authentication│    │ • Memory Mgmt   │   │ • Redis         │
│ • Task Execution│    │ • Auth API      │   │ • Nginx         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL**: Primary database for persistent storage
- **Redis**: Session storage and caching
- **Pydantic**: Data validation and settings management
- **JWT**: Authentication and authorization
- **Uvicorn**: ASGI server

### Frontend
- **React 19**: Latest React with modern features
- **TypeScript**: Type-safe JavaScript development
- **Tailwind CSS**: Utility-first CSS framework
- **React Router**: Client-side routing
- **Vite**: Fast build tool and dev server

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-service orchestration
- **GitHub Actions**: CI/CD pipeline
- **Pre-commit**: Code quality hooks

## 📋 Prerequisites

- **Docker & Docker Compose**
- **Node.js 18+** (for frontend development)
- **Python 3.11+** (for backend development)
- **Git**

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd forge1
```

### 2. Start the Backend

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp env.example .env

# Start development server
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 5. Login

Use any email with password: `admin`

## 🔧 Development Setup

### Shared Package (common libs)

Install the shared package in editable mode so both apps can import it without duplication:

```bash
# From repo root
pip install -e ./shared

# Or inside a specific venv
cd backend && pip install -e ../shared
# (when testing-app exists)
cd testing-app && pip install -e ../shared
```

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://forge:forge@localhost:5432/forge"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="your-secret-key"

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run type checking
npm run type-check

# Run linter
npm run lint

# Start development server
npm run dev
```

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U forge -d forge

# Access Redis CLI
docker-compose exec redis redis-cli

# Reset database
docker-compose down -v
docker-compose up -d
```

## 📁 Project Structure

```
forge1/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core functionality
│   │   │   ├── orchestrator/  # AI orchestration
│   │   │   └── memory/     # Memory management
│   │   ├── db/             # Database models
│   │   └── main.py         # Application entry point
│   ├── requirements.txt    # Python dependencies
│   └── pyproject.toml      # Project configuration
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── config.ts       # Configuration
│   │   └── App.tsx         # Main app component
│   ├── package.json        # Node dependencies
│   └── tailwind.config.js  # Tailwind configuration
├── docker-compose.yml      # Service orchestration
├── .github/                # GitHub Actions workflows
└── README.md               # This file
```

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info

### AI Operations
- `POST /api/v1/ai/execute` - Execute AI task
- `GET /api/v1/ai/models` - List available models
- `GET /api/v1/ai/capabilities` - List task capabilities
- `GET /api/v1/ai/health` - AI orchestrator health

### System
- `GET /api/v1/health` - System health check

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_ai_orchestrator.py
```

### Frontend Tests

```bash
cd frontend

# Run tests (when configured)
npm test

# Run type checking
npm run type-check

# Run linter
npm run lint
```

### Integration Tests

```bash
# Start services
docker-compose up -d

# Run integration tests
pytest tests/integration/

# Cleanup
docker-compose down
```

## 🚀 Deployment

### Production Build

```bash
# Backend
cd backend
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend
npm run build
# Deploy dist/ directory to your hosting service
```

### Docker Deployment

```bash
# prod stack
docker compose --profile prod up --build

# testing stack (sandbox)
docker compose --profile testing -f testing-app/docker-compose.testing.yml up --build
```

### Environment Variables

#### Backend (.env)
```bash
ENV=production
JWT_SECRET=your-secure-secret
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port/0
BACKEND_CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
```

#### Frontend (.env)
```bash
VITE_API_URL=https://api.yourdomain.com
VITE_ENVIRONMENT=production
VITE_APP_VERSION=1.0.0
```

## 🔒 Security

- **JWT Authentication**: Secure token-based authentication
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic models for request validation
- **Environment Variables**: Secure configuration management
- **HTTPS**: Production deployments should use HTTPS

## 📊 Monitoring

- **Health Checks**: Comprehensive service health monitoring
- **Logging**: Structured logging with configurable levels
- **Metrics**: Performance and usage metrics (when configured)
- **Error Tracking**: Error boundaries and logging

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Follow the coding standards
4. **Run tests**: Ensure all tests pass
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**: Describe your changes clearly

### Coding Standards

- **Python**: Follow PEP 8, use type hints, add docstrings
- **TypeScript**: Use strict mode, proper types, consistent naming
- **React**: Functional components with hooks, proper error handling
- **CSS**: Use Tailwind utilities, maintain responsive design

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running: `docker-compose ps postgres`
   - Verify connection string in environment variables
   - Check logs: `docker-compose logs postgres`

2. **Redis Connection Failed**
   - Check Redis is running: `docker-compose ps redis`
   - Verify Redis URL in environment variables
   - Check logs: `docker-compose logs redis`

3. **Frontend Build Errors**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check TypeScript errors: `npm run type-check`
   - Verify environment variables

4. **Authentication Issues**
   - Check JWT secret is set
   - Verify token expiration
   - Check CORS configuration

### Getting Help

- Check the logs: `docker-compose logs -f [service]`
- Review environment variables
- Check GitHub Issues for known problems
- Create a new issue with detailed information

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI team for the excellent web framework
- React team for the amazing frontend library
- Tailwind CSS team for the utility-first CSS framework
- All contributors and maintainers

## 📞 Support

For support and questions:
- Create a GitHub Issue
- Check the documentation
- Review the troubleshooting section

---

**Forge 1** - Building the future of AI orchestration, one task at a time. 🚀

