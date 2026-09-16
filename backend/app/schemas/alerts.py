"""Request and response shapes for the alert investigation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.network import AlertSeverity, AlertStatus


class AlertStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AlertStatus
    note: str | None = Field(default=None, max_length=2000)


class AlertNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=2000)


class AlertEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    from_status: AlertStatus | None
    to_status: AlertStatus | None
    note: str | None
    actor_user_id: UUID | None
    created_at: datetime


class TargetHost(BaseModel):
    ip_address: str
    hostname: str | None = None
    entity_type: str | None = None


class AlertResponse(BaseModel):
    id: UUID
    prediction_id: UUID
    status: AlertStatus
    severity: AlertSeverity
    title: str
    summary: str
    risk_score: float
    risk_level: str
    predicted_attack_type: str | None
    predicted_stage: str | None
    confidence_score: float
    is_fallback: bool
    is_uncertain: bool
    is_ood: bool
    forecast_window_start: datetime
    forecast_window_end: datetime
    target_host: TargetHost | None
    recommended_actions: list[str]
    top_feature_contributors: list[dict[str, Any]]
    created_at: datetime
    resolved_at: datetime | None


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    next_cursor: str | None = None


class AlertDetailResponse(AlertResponse):
    events: list[AlertEventResponse] = []
