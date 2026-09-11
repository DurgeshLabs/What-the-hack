"""A small next-window dynamics model plus MITRE-stage prediction head."""

from __future__ import annotations

import torch
import torch.nn as nn

from ai.inference.contract import FEATURE_NAMES

FEATURE_DIM = len(FEATURE_NAMES)
HIDDEN_DIM = 64
NUM_STAGES = 6


class DynamicsModel(nn.Module):
    """Predict the next 60-second feature window from recent windows."""

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.lstm = nn.LSTM(feature_dim, hidden_dim, num_layers=2, batch_first=True, dropout=0.1)
        self.next_state_head = nn.Linear(hidden_dim, feature_dim)

    def forward(self, history: torch.Tensor, hidden=None):
        output, hidden = self.lstm(history, hidden)
        return self.next_state_head(output[:, -1, :]), hidden

    def rollout(self, history: torch.Tensor, k_steps: int) -> torch.Tensor:
        """Autoregressively forecast ``k_steps`` feature windows."""
        if history.ndim != 3 or history.shape[-1] != self.lstm.input_size:
            raise ValueError("history must have shape (batch, seq_len, feature_dim)")
        states, current = [], history
        for _ in range(k_steps):
            # Do not carry hidden state: ``current`` already includes all history.
            next_state, _ = self(current)
            states.append(next_state)
            current = torch.cat((current[:, 1:, :], next_state.unsqueeze(1)), dim=1)
        return torch.stack(states, dim=1)


class RiskStageHead(nn.Module):
    """Map one real or predicted window to risk probability and attack stage."""

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = 32, num_stages: int = NUM_STAGES):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.risk_out = nn.Linear(hidden_dim, 1)
        self.stage_out = nn.Linear(hidden_dim, num_stages)

    def forward(self, state: torch.Tensor):
        encoded = self.trunk(state)
        return torch.sigmoid(self.risk_out(encoded)).squeeze(-1), self.stage_out(encoded)


class WorldModel(nn.Module):
    """Save/load wrapper for the dynamics and risk/stage networks."""

    def __init__(self, feature_dim: int = FEATURE_DIM):
        super().__init__()
        self.dynamics = DynamicsModel(feature_dim)
        self.risk_stage = RiskStageHead(feature_dim)

    def forecast(self, history: torch.Tensor, k_steps: int):
        states = self.dynamics.rollout(history, k_steps)
        batch, steps, dimensions = states.shape
        risk, logits = self.risk_stage(states.reshape(batch * steps, dimensions))
        return {
            "future_states": states,
            "risk_timeline": risk.reshape(batch, steps),
            "stage_logits": logits.reshape(batch, steps, -1),
        }
