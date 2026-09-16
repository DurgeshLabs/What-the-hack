"""
Alert lifecycle: status transitions, the audit timeline, and alert creation.

Every status change writes two rows: an `alert_events` entry that the analyst UI shows as a
timeline, and an `audit_logs` entry for the tamper-evident trail. Nothing mutates an alert
without both.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.network import (
    Alert,
    AlertEvent,
    AlertSeverity,
    AlertStatus,
    AuditLog,
    Prediction,
    User,
)

# An analyst may triage forward, step back while investigating, or reopen a resolved alert.
# Anything outside this map is rejected so the timeline stays meaningful.
ALLOWED_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.OPEN: {AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING, AlertStatus.RESOLVED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.INVESTIGATING, AlertStatus.RESOLVED, AlertStatus.OPEN},
    AlertStatus.INVESTIGATING: {AlertStatus.RESOLVED, AlertStatus.ACKNOWLEDGED},
    AlertStatus.RESOLVED: {AlertStatus.INVESTIGATING},
}


class InvalidTransition(Exception):
    """Raised when a requested status change is not allowed from the current status."""

    def __init__(self, current: AlertStatus, requested: AlertStatus):
        allowed = sorted(status.value for status in ALLOWED_TRANSITIONS[current])
        super().__init__(f"Cannot move an alert from '{current.value}' to '{requested.value}'. Allowed: {', '.join(allowed)}")
        self.current = current
        self.requested = requested
        self.allowed = allowed


def alert_query(status: AlertStatus | None = None, severity: AlertSeverity | None = None) -> Select:
    """Alerts joined to their prediction, newest first, optionally filtered."""
    query = (
        select(Alert, Prediction)
        .join(Prediction, Prediction.id == Alert.prediction_id)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
    )
    if status is not None:
        query = query.where(Alert.status == status)
    if severity is not None:
        query = query.where(Alert.severity == severity)
    return query


def change_status(
    db: Session, alert: Alert, requested: AlertStatus, actor: User, note: str | None = None
) -> AlertEvent:
    """
    Apply a status transition, recording it in `alert_events` and `audit_logs`.

    The caller commits. Raises InvalidTransition for a disallowed move.
    """
    current = alert.status
    if requested == current:
        raise InvalidTransition(current, requested)
    if requested not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(current, requested)

    alert.status = requested
    alert.resolved_at = datetime.now(timezone.utc) if requested is AlertStatus.RESOLVED else None

    event = AlertEvent(
        alert_id=alert.id,
        actor_user_id=actor.id,
        event_type=f"status.{requested.value}",
        from_status=current,
        to_status=requested,
        note=note,
    )
    db.add(event)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            action="alert.status_changed",
            resource_type="alert",
            resource_id=alert.id,
            metadata_json={"from": current.value, "to": requested.value, "note": note},
        )
    )
    db.flush()
    return event


def add_note(db: Session, alert: Alert, actor: User, note: str) -> AlertEvent:
    """Record an analyst comment without changing the status."""
    event = AlertEvent(alert_id=alert.id, actor_user_id=actor.id, event_type="comment", note=note)
    db.add(event)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            action="alert.commented",
            resource_type="alert",
            resource_id=alert.id,
            metadata_json={"note": note},
        )
    )
    db.flush()
    return event


def timeline(db: Session, alert_id: UUID) -> list[AlertEvent]:
    return list(
        db.scalars(
            select(AlertEvent).where(AlertEvent.alert_id == alert_id).order_by(AlertEvent.created_at.asc())
        )
    )
