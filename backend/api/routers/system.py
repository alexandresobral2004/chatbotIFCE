"""Rotas de sistema: raiz e verificação de saúde."""
from fastapi import APIRouter
from api.container import database_url, llm_provider_name, _llm_provider

router = APIRouter()


# --- Health Check ---
@router.get("/health")
async def health_check():
    try:
        models = await _llm_provider.list_models()
    except Exception:
        models = []
    return {
        "status": "healthy",
        "database": database_url.split("@")[1].split("/")[0] if "@" in database_url else "unknown",
        "llm_provider": "OpenAI" if llm_provider_name == "openai" else llm_provider_name.capitalize(),
        "model": getattr(_llm_provider, "model", "gpt-4o-mini"),
        "models_available": models[:5] if models else [],
    }


# --- Root ---
@router.get("/")
async def root():
    return {
        "message": "RAG Chat Backend API is running",
        "docs": "/docs",
        "endpoint": "POST /chat/{session_id}",
    }
