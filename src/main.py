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

from src.core.config import settings
from src.core.database import Base, engine
from src.exceptions import AppError
from src.routers import auth, transactions, analytics

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
    from src.models import user, transaction  # noqa: F401
    
    # Safe initialization (does not drop tables)
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")
    
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
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Core"], summary="API Root endpoint")
def root():
    return {"status": "running"}

@app.get("/health", tags=["Health"], summary="API health check")
def default_health():
    return {"status": "ok"}

@app.get("/api/health", tags=["Health"], summary="Detailed health check")
def api_health_check():
    return {
        "success": True,
        "message": f"{settings.APP_NAME} v{settings.APP_VERSION} is running",
    }
