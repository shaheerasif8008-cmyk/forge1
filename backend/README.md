# Forge 1 Backend

A modern FastAPI backend for the Forge 1 AI orchestration platform, featuring multi-model AI integration, user authentication, and scalable architecture.

## Features

- **FastAPI Framework**: Modern, fast web framework with automatic API documentation
- **Multi-Model AI Integration**: Support for OpenAI GPT, Anthropic Claude, and Google Gemini
- **User Authentication**: JWT-based authentication system with session management
- **Database Integration**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis integration for session storage and caching
- **Type Safety**: Full type hints with MyPy support
- **Code Quality**: Ruff linting and Black formatting
- **Testing**: Comprehensive test suite with pytest

## Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker and Docker Compose (optional)

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd backend
   ```

2. **Copy environment template:**
   ```bash
   cp env.example .env
   ```

3. **Edit `.env` file with your configuration:**
   ```bash
   # Required
   JWT_SECRET=your-secure-jwt-secret
   
   # Optional - for AI model access
   OPENAI_API_KEY=your-openai-key
   ANTHROPIC_API_KEY=your-anthropic-key
   GOOGLE_AI_API_KEY=your-google-key
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Access the API:**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL:**
   ```bash
   createdb forge
   ```

3. **Set up Redis:**
   ```bash
   redis-server
   ```

4. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your database and Redis URLs
   ```

5. **Initialize database:**
   ```bash
   python -m app.db.init_db
   ```

6. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Development

### Code Quality

The project uses several tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatter
- **MyPy**: Static type checker
- **Pre-commit**: Git hooks for code quality

**Install pre-commit hooks:**
```bash
pre-commit install
```

**Run quality checks manually:**
```bash
# Lint with Ruff
ruff check .

# Format with Black
black .

# Type check with MyPy
mypy app
```

### Testing

**Run tests:**
```bash
pytest
```

**Run tests with coverage:**
```bash
pytest --cov=app --cov-report=html
```

### Database Migrations

**Create a new migration:**
```bash
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback migrations:**
```bash
alembic downgrade -1
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info

### Health
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/ready` - Detailed health check with dependencies
- `GET /api/v1/health/live` - Liveness probe

## AI Model Integration

The backend includes adapters for multiple AI providers:

- **OpenAI GPT**: General purpose AI tasks
- **Anthropic Claude**: Creative and analytical tasks
- **Google Gemini**: Code generation and analysis

To enable AI models, set the corresponding API keys in your `.env` file.

## Project Structure

```
backend/
├── app/
│   ├── api/           # API endpoints and routers
│   ├── core/          # Core configuration and business logic
│   │   └── orchestrator/  # AI model orchestration
│   ├── db/            # Database models and session management
│   ├── routers/       # Additional route modules
│   └── services/      # Business logic services
├── alembic/           # Database migrations
├── tests/             # Test suite
├── docker-compose.yml # Docker services configuration
├── Dockerfile         # Backend container definition
└── requirements.txt   # Python dependencies
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment (dev/prod) | `dev` |
| `JWT_SECRET` | JWT signing secret | `change-me` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://forge:forge@localhost:5432/forge` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `BACKEND_CORS_ORIGINS` | CORS allowed origins | `*` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENAI_API_KEY` | OpenAI key for LLMs/embeddings | - |
| `ANTHROPIC_API_KEY` | Anthropic key for LLMs | - |
| `GOOGLE_AI_API_KEY` | Google Generative AI key | - |
| `PGVECTOR` | Ensure pgvector extension is enabled in Postgres | - |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks
5. Submit a pull request

## License

This project is licensed under the MIT License.
