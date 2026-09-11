"""Train a world model from the project's labeled uploaded-flow CSV format."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from ai.feature_engineering.labeled_windows import build_labeled_windows
from ai.inference.contract import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from ai.models.world_model import DynamicsModel, RiskStageHead, WorldModel

SEQ_LEN, BATCH_SIZE, LR = 10, 64, 1e-3


class WindowSequenceDataset(Dataset):
    """Teacher-forced input history and the immediately following labelled window."""
    def __init__(self, features, risk_labels, stage_labels, seq_len: int = SEQ_LEN):
        self.features = torch.as_tensor(features, dtype=torch.float32)
        self.risk_labels = torch.as_tensor(risk_labels, dtype=torch.float32)
        self.stage_labels = torch.as_tensor(stage_labels, dtype=torch.long)
        self.seq_len = seq_len
        if len(self.features) <= seq_len: raise ValueError(f"Need more than {seq_len} traffic windows.")

    def __len__(self): return len(self.features) - self.seq_len

    def __getitem__(self, index):
        target = index + self.seq_len
        return self.features[index:target], self.features[target], self.risk_labels[target], self.stage_labels[target]


def _fit(model, loader, loss_for, epochs: int, name: str):
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    model.train()
    for epoch in range(epochs):
        total = 0.0
        for batch in loader:
            optimizer.zero_grad(); loss = loss_for(batch); loss.backward(); optimizer.step(); total += loss.item()
        print(f"[{name}] epoch {epoch + 1}/{epochs} loss={total / len(loader):.4f}")


def main(csv_path: str, out_path: str = "ai/models/world_model.pt", epochs: int = 15):
    windows = build_labeled_windows(csv_path)
    mean, std = windows.features.mean(axis=0), windows.features.std(axis=0)
    normalised = (windows.features - mean) / np.where(std < 1e-6, 1.0, std)
    loader = DataLoader(WindowSequenceDataset(normalised, windows.risk_labels, windows.stage_labels), batch_size=BATCH_SIZE, shuffle=True)
    model = WorldModel()
    _fit(model.dynamics, loader, lambda batch: nn.functional.mse_loss(model.dynamics(batch[0])[0], batch[1]), epochs, "dynamics")
    bce, cross_entropy = nn.BCELoss(), nn.CrossEntropyLoss()
    _fit(model.risk_stage, loader, lambda batch: bce(model.risk_stage(batch[1])[0], batch[2]) + cross_entropy(model.risk_stage(batch[1])[1], batch[3]), epochs, "risk/stage")
    destination = Path(out_path); destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "feature_names": list(FEATURE_NAMES), "feature_schema_version": FEATURE_SCHEMA_VERSION, "seq_len": SEQ_LEN, "normalisation": {"mean": mean.tolist(), "std": std.tolist()}}, destination)
    print(f"saved checkpoint to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("csv_path"); parser.add_argument("--out", default="ai/models/world_model.pt"); parser.add_argument("--epochs", type=int, default=15)
    arguments = parser.parse_args(); main(arguments.csv_path, arguments.out, arguments.epochs)
