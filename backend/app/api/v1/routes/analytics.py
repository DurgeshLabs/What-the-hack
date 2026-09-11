"""Read-only data for the analyst dashboard and trained world-model forecast."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_viewer
from app.core.config import settings
from app.db.session import get_db
from app.models.network import TrafficWindow, User, WindowFeature, WindowScope

router = APIRouter(prefix="/analytics")


def _features_for_source(db: Session, source_id: UUID) -> list[tuple[TrafficWindow, WindowFeature]]:
    return list(db.execute(
        select(TrafficWindow, WindowFeature)
        .join(WindowFeature, WindowFeature.traffic_window_id == TrafficWindow.id)
        .where(TrafficWindow.traffic_source_id == source_id, TrafficWindow.scope_type == WindowScope.SOURCE)
        .order_by(TrafficWindow.window_start)
    ).all())


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
    rows = _features_for_source(db, traffic_source_id)
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
    return result
