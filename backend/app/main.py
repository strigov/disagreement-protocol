from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Local tool: no migration engine, the schema is created on startup.
    import app.models  # noqa: F401
    from app.db.base import Base
    from app.db.session import engine

    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Disagreement Protocol", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    from app.api import documents, protocols, files

    app.include_router(documents.router)
    app.include_router(protocols.router)
    app.include_router(files.router)
    return app


app = create_app()
