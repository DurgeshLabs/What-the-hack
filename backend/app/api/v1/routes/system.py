"""Admin surface: registered models, pipeline counts, configuration, and the audit trail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.db.session import get_db
from app.models.network import (
    Alert,
    AlertStatus,
    AuditLog,
    IngestionJob,
    ModelVersion,
    Prediction,
    RawFlow,
    Role,
    TrafficSource,
    TrafficWindow,
    User,
)
from app.services import forecasting

router = APIRouter(prefix="/system")


@router.get("/overview")
def system_overview(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    """Everything the admin page shows. Admin only."""
    counts = {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "traffic_sources": db.scalar(select(func.count()).select_from(TrafficSource)) or 0,
        "ingestion_jobs": db.scalar(select(func.count()).select_from(IngestionJob)) or 0,
        "raw_flows": db.scalar(select(func.count()).select_from(RawFlow)) or 0,
        "traffic_windows": db.scalar(select(func.count()).select_from(TrafficWindow)) or 0,
        "predictions": db.scalar(select(func.count()).select_from(Prediction)) or 0,
        "alerts": db.scalar(select(func.count()).select_from(Alert)) or 0,
    }
    alerts_by_status = {
        status.value: db.scalar(select(func.count()).select_from(Alert).where(Alert.status == status)) or 0
        for status in AlertStatus
    }
    fallback_predictions = db.scalar(select(func.count()).select_from(Prediction).where(Prediction.is_fallback.is_(True))) or 0

    users = [
        {"email": email, "display_name": display_name, "role": role.value, "is_active": is_active, "last_login_at": last_login.isoformat() if last_login else None}
        for email, display_name, role, is_active, last_login in db.execute(
            select(User.email, User.display_name, Role.name, User.is_active, User.last_login_at)
            .join(Role, Role.id == User.role_id)
            .order_by(User.email)
        ).all()
    ]
    models = [
        {
            "name": model.name,
            "version": model.version,
            "feature_schema_version": model.feature_schema_version,
            "artifact_uri": model.artifact_uri,
            "is_active": model.is_active,
            "metrics": model.metrics_json,
            "created_at": model.created_at.isoformat(),
        }
        for model in db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))
    ]
    return {
        "counts": counts,
        "alerts_by_status": alerts_by_status,
        "fallback_predictions": fallback_predictions,
        "users": users,
        "models": models,
        "configuration": {
            "environment": settings.environment,
            "traffic_window_seconds": settings.traffic_window_seconds,
            "forecast_steps": forecasting.FORECAST_STEPS,
            "max_upload_size_mb": settings.max_upload_size_mb,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "login_rate_limit_per_minute": settings.login_rate_limit_per_minute,
            "upload_rate_limit_per_minute": settings.upload_rate_limit_per_minute,
            "checkpoint_configured": bool(settings.world_model_checkpoint),
            "checkpoint_present": forecasting.checkpoint_available(),
            "uses_default_jwt_secret": settings.uses_default_jwt_secret,
        },
    }


@router.get("/audit")
def audit_trail(
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Most recent audit entries, newest first. Admin only."""
    rows = db.execute(
        select(AuditLog, User.email)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(entry.id),
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": str(entry.resource_id) if entry.resource_id else None,
                "actor_email": email,
                "metadata": entry.metadata_json,
                "created_at": entry.created_at.isoformat(),
            }
            for entry, email in rows
        ]
    }
