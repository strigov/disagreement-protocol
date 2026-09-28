from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.request_guard import ALLOWED_ORIGINS, LocalRequestGuard


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from app.db.migrations import upgrade_schema
    from app.db.session import SessionLocal, engine
    from app.services.processing import recover_interrupted_documents

    upgrade_schema(engine)
    with SessionLocal() as db:
        recover_interrupted_documents(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Disagreement Protocol", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(ALLOWED_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LocalRequestGuard)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    from app.api import documents, protocols, files

    app.include_router(documents.router)
    app.include_router(protocols.router)
    app.include_router(files.router)
    return app


app = create_app()
