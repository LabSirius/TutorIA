import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import Base, engine
from app.routers import analytics, chat, evaluations, sessions, students
from app.services import prompt_manager
from app.services.embedding_client import EmbeddingModelUnavailableError
from app.services.rag_service import embedding_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO(tech-debt): remove this create_all bootstrap. Alembic migrations are
    # the single source of truth for the schema going forward. This line
    # predates the move to Alembic + PostgreSQL and must be deleted once app
    # startup no longer relies on it (it cannot create the pgvector HNSW index
    # or the vector extension anyway).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Startup check: the RAG pipeline needs the embedding model pulled in Ollama.
    try:
        await embedding_client.verify_available()
        logger.info("Embedding model '%s' is available.", settings.embedding_model)
    except EmbeddingModelUnavailableError as exc:
        if settings.require_embedding_model:
            raise
        logger.warning(
            "RAG embedding model unavailable at startup: %s "
            "Continuing because REQUIRE_EMBEDDING_MODEL is false; RAG requests "
            "will fail until the model is pulled (ollama pull %s).",
            exc, settings.embedding_model,
        )

    # Warm the pedagogical prompt cache from the database (RF-21).
    count = await prompt_manager.warm_cache()
    if count == 0:
        logger.warning(
            "No active prompt templates found. Seed them with: "
            "python -m app.db.seed prompts"
        )

    yield
    await engine.dispose()


app = FastAPI(
    title="TutorIA API",
    description="AI-powered virtual tutor for rural higher education in Risaralda, Colombia",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(students.router)
app.include_router(evaluations.router)
app.include_router(analytics.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
