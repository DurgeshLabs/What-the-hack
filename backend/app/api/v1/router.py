from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.ingestion import router as ingestion_router
from app.api.v1.routes.windows import router as windows_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.alerts import router as alerts_router
from app.api.v1.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(ingestion_router, tags=["ingestion"])
api_router.include_router(windows_router, tags=["windows"])
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(alerts_router, tags=["alerts"])
api_router.include_router(system_router, tags=["system"])
