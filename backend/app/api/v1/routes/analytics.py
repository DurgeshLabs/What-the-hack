"""Read-only data for the analyst dashboard and trained world-model forecast."""

from datetime import timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, require_viewer
from app.core.config import settings
from app.db.session import get_db
from app.models.network import Alert, AlertSeverity, AlertStatus, Prediction, RiskLevel, TrafficWindow, User, WindowFeature, WindowScope

router = APIRouter(prefix="/analytics")


def _features_for_source(db: Session, source_id: UUID) -> list[tuple[TrafficWindow, WindowFeature]]:
    return list(db.execute(
        select(TrafficWindow, WindowFeature)
        .join(WindowFeature, WindowFeature.traffic_window_id == TrafficWindow.id)
        .where(TrafficWindow.traffic_source_id == source_id, TrafficWindow.scope_type == WindowScope.SOURCE)
        .order_by(TrafficWindow.window_start)
    ).all())


def _run_forecast(db: Session, source_id: UUID) -> tuple[dict, TrafficWindow]:
    rows = _features_for_source(db, source_id)
    if not settings.world_model_checkpoint or not Path(settings.world_model_checkpoint).is_file():
        raise HTTPException(status_code=503, detail="WORLD_MODEL_CHECKPOINT is not configured with a trained artifact")
    try:
        from ai.inference.forecast_engine import forecast as run_forecast, load_model
        model, checkpoint = load_model(settings.world_model_checkpoint)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="World-model dependencies are not installed") from exc
    sequence_length = checkpoint["seq_len"]
    if len(rows) < sequence_length:
        raise HTTPException(status_code=422, detail=f"Need {sequence_length} feature windows; only {len(rows)} are available")
    result = run_forecast(model, checkpoint, [features.features_json for _, features in rows[-sequence_length:]])
    result["observed_until"] = rows[-1][0].window_end.isoformat()
    return result, rows[-1][0]


@router.get("/overview")
def overview(
    traffic_source_id: UUID = Query(...), user: User = Depends(require_viewer), db: Session = Depends(get_db)
) -> dict:
    rows = _features_for_source(db, traffic_source_id)
    checkpoint_ready = bool(settings.world_model_checkpoint and Path(settings.world_model_checkpoint).is_file())
    return {
        "traffic_source_id": str(traffic_source_id),
        "window_count": len(rows),
        "model_ready": checkpoint_ready,
        "traffic": [{"timestamp": window.window_end.isoformat(), "packets": window.packet_count, "bytes": window.byte_count, "flows": window.flow_count} for window, _ in rows],
        "latest_features": rows[-1][1].features_json if rows else None,
    }


@router.get("/forecast")
def forecast(
    traffic_source_id: UUID = Query(...), user: User = Depends(require_viewer), db: Session = Depends(get_db)
) -> dict:
    result, _ = _run_forecast(db, traffic_source_id)
    return result


@router.post("/forecast")
def create_forecast(
    traffic_source_id: UUID = Query(...), user: User = Depends(require_analyst), db: Session = Depends(get_db)
) -> dict:
    """Run a forecast and save it as an analyst-visible investigation alert."""
    result, observation = _run_forecast(db, traffic_source_id)
    risks = [float(point["risk_score"]) for point in result["risk_timeline"]]
    risk_score = round(max(risks) * 100, 2)
    level_name = result["peak_risk_level"]
    stage = result.get("peak_risk_stage")
    explanation = result.get("top_feature_contributors", [])
    prediction = Prediction(
        observation_window_id=observation.id,
        forecast_window_start=observation.window_end,
        forecast_window_end=observation.window_end + timedelta(minutes=len(risks)),
        risk_score=risk_score,
        risk_level=RiskLevel(level_name),
        predicted_attack_type=stage,
        confidence_score=round(max(risks), 3),
        explanation_json=explanation,
    )
    db.add(prediction)
    db.flush()
    actions = [
        "Review the highest-contributing traffic features and affected flows.",
        "Validate the MITRE stage against endpoint and authentication telemetry.",
        "Escalate or contain the affected source if the predicted behaviour persists.",
    ]
    alert = Alert(
        prediction_id=prediction.id,
        title=f"Forecasted {stage or 'network'} risk",
        summary=f"The model forecasts {level_name} risk ({risk_score:.0f}/100) in the next {len(risks)} minutes.",
        severity=AlertSeverity(level_name),
        status=AlertStatus.OPEN,
        recommended_actions_json=actions,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"alert_id": str(alert.id), "prediction_id": str(prediction.id), "forecast": result}
