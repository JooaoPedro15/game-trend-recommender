# API FastAPI somente-leitura sobre os mesmos CSVs locais que a CLI (main.py) le.
# Roda em localhost, sem autenticacao (ver docs/superpowers/specs/2026-09-03-...).

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Game Trend Recommender API",
    description="Leitura do ranking, evidencias, watchlist e status do sistema.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

from api.routers import diagnostico, evidencias, meu_canal, ranking, sistema, watchlist

app.include_router(ranking.router)
app.include_router(evidencias.router)
app.include_router(watchlist.router)
app.include_router(meu_canal.router)
app.include_router(diagnostico.router)
app.include_router(sistema.router)
