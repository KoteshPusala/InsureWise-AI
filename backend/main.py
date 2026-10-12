import os
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from db import init_db, recover_stuck_policies
from services.embeddings import preload_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create storage directories, initialize DB, recover stuck policies, and preload model."""
    for d in [settings.UPLOADS_DIR, settings.INDEXES_DIR, settings.REPORTS_DIR]:
        os.makedirs(str(d), exist_ok=True)
    init_db()
    recovered = recover_stuck_policies()
    if recovered:
        print(f"  Recovered {recovered} stuck policy/policies to 'failed' status.")
    preload_embedding_model()
    print(f"  InsureWise AI Backend")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  API Key Configured: {settings.api_key_configured}")
    print(f"  Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    print(f"  Demo Mode: {settings.is_demo}")
    yield


app = FastAPI(
    title="InsureWise AI",
    description="AI-Powered Insurance Policy Intelligence and Claims Assistance",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Include routers
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
