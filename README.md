# URL Shortener API

A backend URL-shortening service built with **FastAPI**, **MySQL**, **Redis**, and **Celery**. The codebase separates API routes, business services, repositories, SQLAlchemy models, and background tasks.

## Features

- JWT-based registration, login, and logout
- Create, list, update, and deactivate short links
- Custom aliases, optional expiry, and password-protected links
- Authenticated, paginated URL management with filtering and sorting
- Redirect caching with Redis
- Click analytics including user-agent-derived browser, device, and OS summaries
- Per-URL daily click summaries and referrer breakdowns
- Redis-backed request rate limiting (user-scoped for authenticated requests and client-IP-scoped otherwise)
- Celery tasks for click recording and expired-link cleanup
- Structured request logging
- Alembic database migrations and GitHub Actions CI

## Technology

| Area | Technology |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Persistence | SQLAlchemy 2 async, MySQL 8, Alembic |
| Cache and rate limiting | Redis |
| Background processing | Celery |
| Testing | pytest, pytest-asyncio, HTTPX, pytest-cov |
| Code quality | Ruff |

## Project structure

```text
app/
├── api/                 # API v1 routes and short-link redirect route
├── core/                # Settings, security, exceptions, logging
├── database/            # Async SQLAlchemy and Redis clients
├── dependencies/        # Authentication and rate-limiting dependencies
├── middleware/          # Request logging middleware
├── models/              # SQLAlchemy ORM models
├── repositories/        # Database access layer
├── schemas/             # Request and response schemas
├── services/            # Application/business logic
├── tests/               # Automated tests
├── utils/               # Shared utilities
└── workers/             # Celery application and tasks
migrations/              # Alembic migrations
.github/workflows/       # Continuous integration
Dockerfile
docker-compose.yml
pyproject.toml
```

## Run with Docker Compose

### Prerequisites

- Docker Engine
- Docker Compose v2

### Start the services

```bash
cp .env.example .env
# Edit .env and replace JWT_SECRET_KEY with a long random value.
docker compose up --build -d
docker compose exec api alembic upgrade head
```

The stack starts the API, MySQL, Redis, a Celery worker, and Celery Beat.

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Local development without Docker

Start MySQL and Redis locally, then update `DATABASE_URL` and `REDIS_URL` in `.env` to point to `127.0.0.1`.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Run the worker and scheduler in separate terminals:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

## API overview

Authentication endpoints are under `/api/v1`:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/register` | Register a user |
| POST | `/api/v1/login` | Log in and obtain a bearer token |
| POST | `/api/v1/logout` | Revoke the current token |
| POST | `/api/v1/urls` | Create a short URL |
| GET | `/api/v1/urls` | List the authenticated user's URLs |
| GET | `/api/v1/urls/popular` | List the authenticated user's most-clicked active URLs |
| GET | `/api/v1/urls/{url_id}` | Get URL details |
| PUT | `/api/v1/urls/{url_id}` | Update a URL |
| DELETE | `/api/v1/urls/{url_id}` | Deactivate a URL |
| GET | `/api/v1/analytics/{url_id}` | Get click analytics for an owned URL |
| GET | `/{short_code}` | Redirect to the destination |

Protected endpoints require `Authorization: Bearer <access_token>`.

### Create a short URL

```http
POST /api/v1/urls
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "original_url": "https://example.com/a/long/path",
  "custom_alias": "my-example",
  "expires_at": null,
  "is_active": true
}
```

## Configuration

Copy `.env.example` to `.env`. The main settings are:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async SQLAlchemy connection URL |
| `REDIS_URL` | Redis connection for cache, rate limits and Celery |
| `JWT_SECRET_KEY` | Secret used to sign access tokens |
| `JWT_ALGORITHM` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime |
| `APP_ENV` | Application environment |
| `DEBUG` | Enable or disable debug mode |

Never commit `.env` or real credentials. Use a unique random `JWT_SECRET_KEY` outside local development.

## Tests

The API tests use an in-memory SQLite database for request-level coverage. Background-task tests also use the configured database and Redis, so start the MySQL and Redis services before running the complete suite.

```bash
python -m pip install -e ".[dev]"
alembic upgrade head
pytest app/tests -v --asyncio-mode=auto --cov=app --cov-report=term-missing
```

## Design notes

- MySQL is the source of truth for users, URLs, and click records.
- Redis is used for redirect caching and rate limiting.
- Celery processes click events and performs scheduled expiry cleanup.
- The popular-URLs endpoint is scoped to the authenticated owner; it does not expose other users' destination URLs.
- Redirect responses are returned even if the background click-event queue is temporarily unavailable; the enqueue failure is logged.
- Forwarded client-IP headers are not trusted by default for rate-limit identity; configure a trusted proxy at the server/ingress layer before using them.

## Current limitations

- Country-level analytics storage exists in the schema, but this application does not currently enrich incoming clicks with geolocation data.
- No benchmark results are claimed; measure performance in a target environment before publishing latency figures.
- This project is a portfolio/learning implementation and should receive a security and operational review before production use.
