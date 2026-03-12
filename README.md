# TrustButVerify Backend

REST API and data store for the TrustButVerify browser extension research project.
Receives synchronised conversation logs, copy activity records, and nudge-event
responses from the extension and persists them in a MySQL database for analysis.

## Architecture

```
Browser Extension  ──HTTP──▶  nginx (reverse proxy, port 80)
                                 │
                                 ▼
                              FastAPI (uvicorn, port 8000)
                                 │
                                 ▼
                              MySQL 8.4 (InnoDB, utf8mb4)
```

All three services run as Docker containers managed by Docker Compose.

## Tech Stack

| Layer       | Technology                              |
|-------------|-----------------------------------------|
| Language    | Python 3.12                             |
| Framework   | FastAPI 0.115                           |
| ORM         | SQLAlchemy 2.0 (async, aiomysql driver) |
| Validation  | Pydantic v2                             |
| Database    | MySQL 8.4                               |
| Proxy       | nginx (Alpine)                          |
| Container   | Docker + Docker Compose                 |

## API Endpoints

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/api/health`                     | Health check (API + database)        |
| POST   | `/api/participants/register`      | Register a new participant (UUID)    |
| GET    | `/api/participants/verify/:uuid`  | Verify a participant UUID            |
| POST   | `/api/sync`                       | Sync extension data to the database  |
| GET    | `/api/debug/data/:uuid`           | Retrieve all data for a participant  |

Interactive docs available at `/api/docs` (Swagger UI) and `/api/redoc`.

## Database Schema

Five tables: `participants`, `conversations`, `conversation_turns`,
`copy_activities`, and `nudge_events`. See `schema.sql` for the full
DDL including indexes and foreign key constraints.

## Prerequisites

- Docker Engine 24+
- Docker Compose v2

## Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/shehan-hetti/trustbutverify-backend.git
   cd trustbutverify-backend
   ```

2. **Create the environment file**

   ```bash
   cp .env.example .env
   # Edit .env with your own passwords
   ```

3. **Start the stack**

   ```bash
   docker compose up -d
   ```

4. **Verify**

   ```bash
   curl http://localhost/api/health
   # {"status":"ok","database":"connected"}
   ```

## Environment Variables

| Variable              | Description                          | Default                |
|-----------------------|--------------------------------------|------------------------|
| `MYSQL_ROOT_PASSWORD` | MySQL root password                  | *(required)*           |
| `MYSQL_DATABASE`      | Database name                        | `trustbutverify`       |
| `MYSQL_USER`          | Application database user            | *(required)*           |
| `MYSQL_PASSWORD`      | Application database password        | *(required)*           |
| `DATABASE_URL`        | SQLAlchemy async connection string   | *(required)*           |
| `API_HOST`            | Uvicorn bind address                 | `0.0.0.0`             |
| `API_PORT`            | Uvicorn port                         | `8000`                 |

## Running Tests

Tests use an in-memory SQLite database and require no external services.

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx aiosqlite
pytest -x --tb=short
```

## Project Structure

```
trustbutverify-backend/
├── app/
│   ├── main.py             # FastAPI application setup
│   ├── config.py           # Pydantic settings from environment
│   ├── database.py         # SQLAlchemy async engine and session
│   ├── models.py           # ORM table definitions
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── routes/
│   │   ├── health.py       # Health check endpoint
│   │   ├── participants.py # Registration and verification
│   │   └── sync.py         # Data synchronisation endpoint
│   └── services/
│       └── sync_service.py # Sync business logic (upsert/dedup)
├── tests/
│   ├── conftest.py         # Fixtures and SQLite test engine
│   ├── test_api.py         # Integration tests (full HTTP)
│   ├── test_helpers.py     # Unit tests for sync_service helpers
│   └── test_schemas.py     # Pydantic schema validation tests
├── docker-compose.yml      # Three-service stack definition
├── Dockerfile              # FastAPI container image
├── nginx.conf              # Reverse proxy configuration
├── schema.sql              # MySQL DDL
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Pytest configuration
└── .gitignore
```

## Licence

This project is licensed under the [GPL-3.0 License](https://www.gnu.org/licenses/gpl-3.0.en.html).
