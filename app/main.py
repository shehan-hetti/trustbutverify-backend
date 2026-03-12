from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routes import health, participants, sync


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle."""
    yield
    # Dispose the DB connection pool on shutdown
    await engine.dispose()


app = FastAPI(
    title="TrustButVerify Backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — allow the browser extension to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # extension origin is chrome-extension://...
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(health.router)
app.include_router(participants.router)
app.include_router(sync.router)
