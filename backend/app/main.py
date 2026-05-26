from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import lifespan
from app.routers import (
    individuals, places, migration, graph, evidence, assistant,
    timeline, pedigree, stats, research_priority, quality,
)

app = FastAPI(
    title="Roots Graph API",
    description="Evidence-first genealogy research platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(individuals.router)
app.include_router(places.router)
app.include_router(migration.router)
app.include_router(graph.router)
app.include_router(evidence.router)
app.include_router(assistant.router)
app.include_router(timeline.router)
app.include_router(pedigree.router)
app.include_router(stats.router)
app.include_router(research_priority.router)
app.include_router(quality.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
