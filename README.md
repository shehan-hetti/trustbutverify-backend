# TrustButVerify Backend

REST API and data store for the TrustButVerify browser extension research project.
Receives synchronised conversation logs, copy activity records, and nudge-event
responses from the extension and persists them in a MySQL database for analysis.

## Architecture

```
Browser Extension  ──HTTPS──▶  nginx (reverse proxy, port 443)
                                   │  (HTTP :80 → 301 redirect)
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
| Proxy       | nginx (Alpine) + TLS                    |
| TLS         | Let's Encrypt (Certbot)                 |
| Container   | Docker + Docker Compose                 |

## API Endpoints

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/api/health`                     | Health check (API + database)        |
| POST   | `/api/participants/register`      | Register a new participant (UUID)    |
| GET    | `/api/participants/verify/:uuid`  | Verify a participant UUID            |
| POST   | `/api/sync`                       | Sync extension data to the database  |
| GET    | `/api/debug/data`               | Debug data view (requires `X-Debug-Key`)  |

Interactive docs available at `/api/docs` (Swagger UI) and `/api/redoc`.

## Database Schema

Five tables: `participants`, `conversations`, `conversation_turns`,
`copy_activities`, and `nudge_events`. See `schema.sql` for the full
DDL including indexes and foreign key constraints.

## SSL / TLS

The nginx reverse proxy terminates TLS using Let's Encrypt certificates
managed by Certbot. Certificates are stored on the host at
`/etc/letsencrypt/` and mounted read-only into the nginx container.

### Setup

```bash
# Install Certbot
sudo apt install -y certbot

# Obtain certificate (stop Docker first to free port 80)
docker compose down
sudo certbot certonly --standalone -d api.trustbutverify.dev
docker compose up -d
```

Certbot automatically sets up a scheduled task for renewal.
Certificates are valid for 90 days and auto-renew.

## Prerequisites

- Docker Engine 24+
- Docker Compose v2
- Certbot (for SSL certificate management)

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

3. **Set up SSL certificate**

   ```bash
   sudo certbot certonly --standalone -d api.trustbutverify.dev
   ```

4. **Start the stack**

   ```bash
   docker compose up -d
   ```

5. **Verify**

   ```bash
   curl https://api.trustbutverify.dev/api/health
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
| `DEBUG_API_KEY`       | API key for `/api/debug/data` endpoint | `""` (disabled)      |

## Debug Data Endpoint

The `/api/debug/data` endpoint returns all stored data for inspection.
It requires the `X-Debug-Key` header matching the `DEBUG_API_KEY` env var.

```bash
# Query all data
curl -s https://api.trustbutverify.dev/api/debug/data \
  -H "X-Debug-Key: YOUR_DEBUG_KEY" | python3 -m json.tool

# Filter by participant
curl -s "https://api.trustbutverify.dev/api/debug/data?participant_uuid=UUID" \
  -H "X-Debug-Key: YOUR_DEBUG_KEY" | python3 -m json.tool

# Without the key → 403 Forbidden
curl -s https://api.trustbutverify.dev/api/debug/data
# → {"detail": "Forbidden"}
```

## Deploying Updates to CSC

The backend runs on a CSC cPouta VM as Docker containers.

### SSH into the VM

```bash
ssh -i <key-file>.pem ubuntu@<BACKEND_VM_IP>
```

### Pull latest code and redeploy

```bash
cd ~/trustbutverify-backend

# Pull latest changes
git pull origin main

# Rebuild and restart (preserves database volume)
docker compose build api
docker compose up -d api

# Verify
curl -s https://api.trustbutverify.dev/api/health
# → {"status":"ok","database":"connected"}
```

### If `.env` changed

```bash
# Edit .env on the VM with new values
nano .env

# Restart the API container to pick up changes
docker compose up -d api
```

### If `schema.sql` changed (new columns/tables)

```bash
# Connect to MySQL to run migrations manually
docker compose exec db mysql -u root -p trustbutverify

# Or apply the full schema (WARNING: only for fresh databases)
# docker compose exec -T db mysql -u root -p trustbutverify < schema.sql
```

### View logs

```bash
# API logs
docker compose logs -f api

# Nginx logs
docker compose logs -f nginx

# All services
docker compose logs -f
```

### Full rebuild (nuclear option)

```bash
# Stop everything, rebuild from scratch (keeps database)
docker compose down
docker compose build --no-cache
docker compose up -d
```

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
├── certbot-webroot/        # ACME challenge webroot (for cert renewal)
├── docker-compose.yml      # Three-service stack definition
├── Dockerfile              # FastAPI container image
├── nginx.conf              # Reverse proxy + TLS configuration
├── schema.sql              # MySQL DDL
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Pytest configuration
└── .gitignore
```

## Licence

This project is licensed under the [GPL-3.0 License](https://www.gnu.org/licenses/gpl-3.0.en.html).
