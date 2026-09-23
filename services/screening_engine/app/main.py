"""FastAPI entrypoint for the screening engine.

Deliberately thin. It accepts work, validates it, records a receipt and
returns. Everything expensive happens on the worker, because a VLM call can
take three minutes and must never hold a request open.
"""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config import get_settings
from app.middleware import RawBodyMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Adamson Screening Engine",
        version="0.1.0",
        # Not public. Reachable only from Frappe on the internal network.
        description="Private AI screening service. No public ingress.",
    )
    # Outermost: the signature covers bytes that must be captured before any
    # other layer reads the request stream.
    app.add_middleware(RawBodyMiddleware, max_body_bytes=settings.max_upload_bytes)
    app.include_router(api_router, prefix="/v1")

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
