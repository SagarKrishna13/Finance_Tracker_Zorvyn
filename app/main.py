"""
Finance Tracker API - entry point.

Responsibilities:
  1. Create all DB tables on startup (lifespan event)
  2. Register all routers with their URL prefixes
  3. Install global exception handlers so every error returns
     a consistent JSON envelope regardless of where it was raised
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import Base, engine
from app.exceptions import AppError
from app.routers import auth, transactions, analytics

# Structured logging - shows in uvicorn output and is easy to grep
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan - runs once on startup and once on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import models so SQLAlchemy registers them
    from app.models import user, transaction  # noqa: F401
    from app.core.seed import run as seed_db

    # Always drop logic to ensure a fresh app startup state 
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped for fresh start")

    # Create tables and run seed
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified")
    seed_db()
    
    yield
    logger.info("Application shutting down")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A clean, role-based finance tracking API. "
        "Supports CRUD, pagination, search, analytics, and CSV/JSON export."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    Catches every custom AppError subclass (NotFoundError, ForbiddenError, etc.)
    and returns a consistent JSON error envelope.
    """
    logger.warning(f"{exc.__class__.__name__}: {exc.message} | path={request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Reformat Pydantic's 422 errors into the same envelope shape as AppError.
    Picks the first validation error to keep the response simple.
    """
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
    message = first_error["msg"].replace("Value error, ", "")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
                "field": field or None,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """
    Catch-all for anything unexpected (DB connection loss, bugs, etc.).
    Logs the full traceback server-side; returns a safe generic message to the client.
    """
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "field": None,
            },
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["Health"], summary="API health check")
def health_check():
    return {
        "success": True,
        "message": f"{settings.APP_NAME} v{settings.APP_VERSION} is running",
    }

# ---------------------------------------------------------------------------
# Frontend Static Files
# ---------------------------------------------------------------------------

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # This is /app
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
