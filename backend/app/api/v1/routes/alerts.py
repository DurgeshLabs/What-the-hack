"""Persisted forecast alerts and the analyst investigation workflow."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.models.network import Alert, AlertSeverity, AlertStatus, HostEntity, Prediction, User
from app.schemas.alerts import (
    AlertDetailResponse,
    AlertEventResponse,
    AlertListResponse,
    AlertNoteCreate,
    AlertResponse,
    AlertStatusUpdate,
    TargetHost,
)
from app.services import alerts as alert_service

router = APIRouter(prefix="/alerts")


def _payload(alert: Alert, prediction: Prediction, host: HostEntity | None) -> dict:
    return {
        "id": alert.id,
        "prediction_id": prediction.id,
        "status": alert.status,
        "severity": alert.severity,
        "title": alert.title,
        "summary": alert.summary,
        "risk_score": float(prediction.risk_score),
        "risk_level": prediction.risk_level.value,
        "predicted_attack_type": prediction.predicted_attack_type,
        "predicted_stage": prediction.predicted_stage,
        "confidence_score": float(prediction.confidence_score),
        "is_fallback": prediction.is_fallback,
        "is_uncertain": prediction.is_uncertain,
        "is_ood": prediction.is_ood,
        "forecast_window_start": prediction.forecast_window_start,
        "forecast_window_end": prediction.forecast_window_end,
        "target_host": TargetHost(ip_address=host.ip_address, hostname=host.hostname, entity_type=host.entity_type) if host else None,
        "recommended_actions": alert.recommended_actions_json,
        "top_feature_contributors": prediction.explanation_json,
        "created_at": alert.created_at,
        "resolved_at": alert.resolved_at,
    }


def _load(db: Session, alert_id: UUID) -> tuple[Alert, Prediction, HostEntity | None]:
    row = db.execute(
        select(Alert, Prediction).join(Prediction, Prediction.id == Alert.prediction_id).where(Alert.id == alert_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert, prediction = row
    host = db.get(HostEntity, alert.target_host_id) if alert.target_host_id else None
    return alert, prediction, host


@router.get("", response_model=AlertListResponse)
def list_alerts(
    alert_status: AlertStatus | None = Query(default=None, alias="status", description="Filter by workflow status"),
    severity: AlertSeverity | None = Query(default=None, description="Filter by severity"),
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None, description="Return alerts created before this timestamp (the previous page's next_cursor)"),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """Alerts in operational priority order: newest first, optionally filtered."""
    query = alert_service.alert_query(alert_status, severity).limit(limit + 1)
    if before is not None:
        query = query.where(Alert.created_at < before)
    rows = db.execute(query).all()

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = rows[-1][0].created_at.isoformat()

    host_ids = {alert.target_host_id for alert, _ in rows if alert.target_host_id}
    hosts = {host.id: host for host in db.scalars(select(HostEntity).where(HostEntity.id.in_(host_ids)))} if host_ids else {}
    items = [AlertResponse(**_payload(alert, prediction, hosts.get(alert.target_host_id))) for alert, prediction in rows]
    return AlertListResponse(items=items, next_cursor=next_cursor)


@router.get("/{alert_id}", response_model=AlertDetailResponse)
def alert_detail(alert_id: UUID, user: User = Depends(require_viewer), db: Session = Depends(get_db)) -> AlertDetailResponse:
    alert, prediction, host = _load(db, alert_id)
    events = [AlertEventResponse.model_validate(event) for event in alert_service.timeline(db, alert_id)]
    return AlertDetailResponse(**_payload(alert, prediction, host), events=events)


@router.patch("/{alert_id}/status", response_model=AlertDetailResponse)
def update_alert_status(
    alert_id: UUID,
    payload: AlertStatusUpdate,
    user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> AlertDetailResponse:
    """Acknowledge, investigate, resolve, or reopen an alert. Analyst or admin only."""
    alert, prediction, host = _load(db, alert_id)
    try:
        alert_service.change_status(db, alert, payload.status, user, payload.note)
    except alert_service.InvalidTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "current_status": exc.current.value, "allowed": exc.allowed},
        ) from exc
    db.commit()
    db.refresh(alert)
    events = [AlertEventResponse.model_validate(event) for event in alert_service.timeline(db, alert_id)]
    return AlertDetailResponse(**_payload(alert, prediction, host), events=events)


@router.post("/{alert_id}/notes", response_model=AlertEventResponse, status_code=status.HTTP_201_CREATED)
def add_alert_note(
    alert_id: UUID,
    payload: AlertNoteCreate,
    user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> AlertEventResponse:
    """Add an investigation note without changing the status."""
    alert, _, _ = _load(db, alert_id)
    event = alert_service.add_note(db, alert, user, payload.note)
    db.commit()
    db.refresh(event)
    return AlertEventResponse.model_validate(event)


@router.get("/{alert_id}/events", response_model=list[AlertEventResponse])
def alert_events(alert_id: UUID, user: User = Depends(require_viewer), db: Session = Depends(get_db)) -> list[AlertEventResponse]:
    _load(db, alert_id)
    return [AlertEventResponse.model_validate(event) for event in alert_service.timeline(db, alert_id)]
