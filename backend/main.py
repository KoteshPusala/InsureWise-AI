import os
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from db import init_db, recover_stuck_policies, get_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lightweight, deterministic startup hook.
    Creates storage directories, initializes SQLite, recovers stuck policies,
    and binds to $PORT immediately without blocking on heavy models.
    """
    for d in [settings.UPLOADS_DIR, settings.INDEXES_DIR, settings.REPORTS_DIR]:
        os.makedirs(str(d), exist_ok=True)
    init_db()
    recovered = recover_stuck_policies()
    if recovered:
        print(f"  Recovered {recovered} stuck policy/policies to 'failed' status.")

    # Measure and log startup memory footprint
    try:
        import psutil
        rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        print(f"  Startup memory footprint: {rss_mb:.1f} MB (Budget: 512 MiB)")
    except Exception:
        pass

    port = os.getenv("PORT", "8000")
    print(f"  InsureWise AI Backend ready on port {port}")
    print(f"  LLM Provider: {settings.LLM_PROVIDER} ({settings.active_model})")
    print(f"  Embedding Provider: {settings.EMBEDDING_PROVIDER} (Lazy loaded on demand)")
    yield


app = FastAPI(
    title="InsureWise AI",
    description="AI-Powered Insurance Policy Intelligence and Claims Assistance",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root-level health & readiness endpoints for Render / cloud probes
@app.get("/health", tags=["system"])
def root_health():
    """Lightweight root health probe for cloud load balancers and Render."""
    mem_mb = 0.0
    try:
        import psutil
        mem_mb = round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    except Exception:
        pass
    return {
        "status": "ok",
        "app": "InsureWise AI",
        "memory_rss_mb": mem_mb,
        "memory_budget_mb": 512,
    }


@app.get("/ready", tags=["system"])
def root_readiness():
    """Readiness probe that validates DB connectivity and storage paths."""
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connectivity check failed: {str(e)}")

    if not os.path.exists(str(settings.STORAGE_DIR)):
        raise HTTPException(status_code=503, detail="Storage directory not accessible")

    return {
        "status": "ready",
        "database": "connected",
        "storage": "writable"
    }


# Global exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "error": {"code": "VALIDATION_ERROR", "message": str(exc)}
        },
    )


@app.exception_handler(FileNotFoundError)
async def not_found_handler(request: Request, exc: FileNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "error": {"code": "NOT_FOUND", "message": str(exc)}
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again.",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
            }
        },
    )


# Include API routers
from routers.health import router as health_router
from routers.policies import router as policies_router
from routers.chat import router as chat_router
from routers.claims import router as claims_router
from routers.auth import router as auth_router

app.include_router(health_router, prefix="/api")
app.include_router(policies_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(claims_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
