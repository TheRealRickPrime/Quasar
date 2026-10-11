from fastapi import FastAPI

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.backups import router as backups_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Quasar backup and cloud orchestration API",
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(backups_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name}
