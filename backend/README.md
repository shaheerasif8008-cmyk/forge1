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

### Structured Logging

Forge 1 backend emits JSON logs with request-scoped trace IDs and tenant context. See `../docs/phase5/logging.md`.

#### Azure Log Analytics

- Container stdout/stderr is collected automatically in Azure environments when Log Analytics is enabled on the container app/AKS cluster.
- Parse logs as JSON in queries to filter by `trace_id`, `tenant_id`, `level`, etc.

#### Local Promtail + Loki (optional)

- A `docker-compose.override.yml` is provided to run Promtail + Loki locally to aggregate container logs.
- Start with: `docker compose -f docker-compose.yml -f docker-compose.override.yml up -d`
- View logs in Grafana (if added) or query directly against Loki’s API.

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
- `POST /api/v1/auth/register` - Create account (email/password), optional tenant
- `POST /api/v1/auth/verify-email` - Verify email via token
- `POST /api/v1/auth/login` - Login (email/username + password; MFA aware)
- `POST /api/v1/auth/refresh` - Rotate refresh and mint new access
- `POST /api/v1/auth/logout` - Revoke refresh session
- `POST /api/v1/auth/request-password-reset` - Request reset email
- `POST /api/v1/auth/reset-password` - Reset with token
- `POST /api/v1/auth/mfa/setup` - Provision TOTP + recovery codes
- `POST /api/v1/auth/mfa/verify` - Verify TOTP or recovery code
- `POST /api/v1/auth/mfa/disable` - Disable MFA and revoke sessions
- `GET /api/v1/auth/me` - Get current user info (legacy)

### Health
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/ready` - Detailed health check with dependencies
- `GET /api/v1/health/live` - Liveness probe

## AI Model Integration

The backend includes adapters for multiple AI providers:

- **OpenAI GPT**: General purpose AI tasks
- **Anthropic Claude**: Creative and analytical tasks
- **Google Gemini**: Code generation and analysis

### Model Routing Matrix

The cost/latency-aware router considers provider availability, circuit-breaker state, admin overrides, and a simple score combining estimated cost and latency p95. Approximate mapping of capabilities:

| Task Type | OpenRouter | OpenAI | Claude | Gemini |
|-----------|-----------:|-------:|-------:|-------:|
| general | ✓ | ✓ | ✓ | ✓ |
| code_generation | ✓ | ✓ | ✓ | ✓ |
| analysis | ✓ | ✓ | ✓ | ✓ |
| creative | ✓ | ✓ | ✓ | ✓ |
| review | ✓ | ✓ | ✓ | ✓ |

Admin overrides (feature flags, per-tenant):
- Force provider: `router.force_provider_openrouter|openai|claude|gemini`
- Disable provider: `router.disable_provider_openrouter|openai|claude|gemini`

Latency SLO can be passed per request via `context.latency_slo_ms`; the router penalizes providers whose p95 exceeds the SLO.

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
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://forge:forge@127.0.0.1:5542/forge1_local` |
| `REDIS_URL` | Redis connection string | `redis://127.0.0.1:6382/0` |
| `BACKEND_CORS_ORIGINS` | CORS allowed origins | `*` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENAI_API_KEY` | OpenAI key for LLMs/embeddings | - |
| `ANTHROPIC_API_KEY` | Anthropic key for LLMs | - |
| `GOOGLE_AI_API_KEY` | Google Generative AI key | - |
| `PGVECTOR` | Ensure pgvector extension is enabled in Postgres | - |
| `PROMPT_CACHE_TTL_SECS` | TTL for prompt cache entries (seconds) | `300` |
| `OPENAI_1K_TOKEN_COST_CENTS` | Approximate cost per 1k tokens for OpenAI (cents) | `10` |
| `CLAUDE_1K_TOKEN_COST_CENTS` | Approximate cost per 1k tokens for Claude (cents) | `16` |
| `GEMINI_1K_TOKEN_COST_CENTS` | Approximate cost per 1k tokens for Gemini (cents) | `8` |
| `OPENROUTER_1K_TOKEN_COST_CENTS` | Approximate cost per 1k tokens for OpenRouter (cents) | `9` |
| `ROUTER_FALLBACK_ORDER` | Fallback provider order | `openrouter,openai,claude,gemini` |
| `CIRCUIT_BREAKER_THRESHOLD` | Failures before circuit opens | `3` |
| `CIRCUIT_BREAKER_COOLDOWN_SECS` | Cooldown before half-open | `60` |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks
5. Submit a pull request

## License

This project is licensed under the MIT License.
