"""World-model inference using the repository's 37-feature contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import torch

from ai.inference.contract import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, risk_level_for, validate_features
from ai.inference.mitre_stage_map import MITRE_STAGES
from ai.models.world_model import WorldModel


def load_model(checkpoint_path: str | Path) -> tuple[WorldModel, dict[str, Any]]:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if checkpoint.get("feature_names") != list(FEATURE_NAMES) or checkpoint.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("Model artifact does not match the active feature schema.")
    model = WorldModel(); model.load_state_dict(checkpoint["state_dict"]); model.eval()
    return model, checkpoint


def forecast(model: WorldModel, checkpoint: dict[str, Any], history: Sequence[dict[str, float]], k_steps: int = 5) -> dict[str, Any]:
    """Forecast a sequence of validated production feature dictionaries."""
    if len(history) != checkpoint["seq_len"]: raise ValueError(f"Expected exactly {checkpoint['seq_len']} history windows.")
    rows = [[validate_features(window)[name] for name in FEATURE_NAMES] for window in history]
    mean, std = checkpoint["normalisation"]["mean"], checkpoint["normalisation"]["std"]
    observed = torch.tensor([[[(value - mean[index]) / (std[index] if std[index] >= 1e-6 else 1.0) for index, value in enumerate(row)] for row in rows]], dtype=torch.float32)
    with torch.no_grad(): output = model.forecast(observed, k_steps)
    risks = output["risk_timeline"][0].tolist(); stage_ids = output["stage_logits"][0].argmax(dim=-1).tolist()
    stages = [MITRE_STAGES[index] for index in stage_ids]; peak = max(range(len(risks)), key=risks.__getitem__)
    return {
        "risk_timeline": [{"step": index + 1, "risk_score": float(risk), "stage": stages[index]} for index, risk in enumerate(risks)],
        "peak_risk_level": risk_level_for(float(risks[peak]) * 100),
        "peak_risk_window": peak + 1,
        "peak_risk_stage": stages[peak],
        "top_feature_contributors": explain_step(model, observed, peak, k_steps),
    }


def explain_step(model: WorldModel, history: torch.Tensor, step_idx: int, k_steps: int, top_n: int = 5):
    observed = history.detach().clone().requires_grad_(True); model.zero_grad(set_to_none=True)
    model.forecast(observed, k_steps)["risk_timeline"][0, step_idx].backward()
    scores = (observed.grad[0] * observed[0]).abs().sum(dim=0)
    total = float(scores.sum().detach()) or 1.0
    return [{"feature": FEATURE_NAMES[index], "contribution": float(scores[index].detach()) / total} for index in torch.argsort(scores, descending=True)[:top_n].tolist()]
