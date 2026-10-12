"""Composition root da API do chat: cria o app, configura o CORS e inclui os routers (api/routers/)."""
import os

# api.container carrega o .env e monta os adapters; precisa vir antes dos routers.
from api.container import _postgres_usage_adapter
from api.routers import auth, chat, project, system
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="JupiterClass Chat API",
    description="Chatbot RAG de metodologia científica (serviço independente)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()],
    ],
    allow_origin_regex=r"https://.*\.railway\.app|http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (chat, system, project, auth):
    app.include_router(module.router)


@app.on_event("startup")
async def startup_event():
    await _postgres_usage_adapter.initialize()
