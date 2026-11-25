from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, community, docs, interviews, learn, problems, submissions
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="LeetCode-style practice platform: problems, auth and progress tracking.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (auth, problems, submissions, learn, docs, interviews, community):
        app.include_router(module.router, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
