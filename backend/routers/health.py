import shutil
from fastapi import APIRouter
from config import settings
from schemas import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    settings.reload_env()
    tesseract_available = shutil.which("tesseract") is not None
    return HealthResponse(
        status="ok",
        llm_provider=settings.LLM_PROVIDER,
        api_key_configured=settings.api_key_configured,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        tesseract_available=tesseract_available,
        demo_mode=settings.is_demo,
    )
