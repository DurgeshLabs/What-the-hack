"""Persisted forecast alerts exposed to the analyst UI."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_viewer
from app.db.session import get_db
from app.models.network import Alert, Prediction, User

router = APIRouter(prefix="/alerts")


def _payload(alert: Alert, prediction: Prediction) -> dict:
    return {
        "id": str(alert.id), "prediction_id": str(prediction.id), "status": alert.status.value,
        "severity": alert.severity.value, "title": alert.title, "summary": alert.summary,
        "risk_score": float(prediction.risk_score), "risk_level": prediction.risk_level.value,
        "predicted_attack_type": prediction.predicted_attack_type, "confidence_score": float(prediction.confidence_score),
        "forecast_window_start": prediction.forecast_window_start.isoformat(), "forecast_window_end": prediction.forecast_window_end.isoformat(),
        "created_at": alert.created_at.isoformat(), "recommended_actions": alert.recommended_actions_json,
        "top_feature_contributors": prediction.explanation_json,
    }


@router.get("")
def list_alerts(user: User = Depends(require_viewer), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(Alert, Prediction).join(Prediction, Prediction.id == Alert.prediction_id).order_by(Alert.created_at.desc())).all()
    return {"items": [_payload(alert, prediction) for alert, prediction in rows], "next_cursor": None}


@router.get("/{alert_id}")
def alert_detail(alert_id: UUID, user: User = Depends(require_viewer), db: Session = Depends(get_db)) -> dict:
    row = db.execute(select(Alert, Prediction).join(Prediction, Prediction.id == Alert.prediction_id).where(Alert.id == alert_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _payload(*row)
