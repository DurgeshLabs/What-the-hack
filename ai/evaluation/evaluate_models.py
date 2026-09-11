"""Chronological held-out benchmark for logistic regression and the world model."""

from __future__ import annotations

import argparse
import json

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix

from ai.feature_engineering.labeled_windows import build_labeled_windows
from ai.inference.forecast_engine import load_model


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {"precision": precision_score(y_true, y_pred, zero_division=0), "recall": recall_score(y_true, y_pred, zero_division=0), "f1": f1_score(y_true, y_pred, zero_division=0), "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0, "support": int(len(y_true))}


def main(csv_path: str, checkpoint_path: str, test_fraction: float = 0.2) -> None:
    data = build_labeled_windows(csv_path)
    split = int(len(data.features) * (1 - test_fraction))
    mean, std = data.features[:split].mean(0), data.features[:split].std(0); x = (data.features - mean) / np.where(std < 1e-6, 1, std)
    baseline = LogisticRegression(max_iter=1000, class_weight="balanced").fit(x[:split], data.risk_labels[:split])
    baseline_scores = metrics(data.risk_labels[split:], baseline.predict(x[split:]))
    model, checkpoint = load_model(checkpoint_path); seq = checkpoint["seq_len"]
    targets, predictions = [], []
    with torch.no_grad():
        for index in range(max(split, seq), len(x)):
            score = model.forecast(torch.tensor(x[index - seq:index], dtype=torch.float32).unsqueeze(0), 1)["risk_timeline"][0, 0].item()
            targets.append(data.risk_labels[index]); predictions.append(score >= 0.5)
    report = {"split": "chronological", "test_fraction": test_fraction, "logistic_regression": baseline_scores, "world_model": metrics(np.asarray(targets), np.asarray(predictions))}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("csv_path"); parser.add_argument("checkpoint_path"); parser.add_argument("--test-fraction", type=float, default=0.2)
    args = parser.parse_args(); main(args.csv_path, args.checkpoint_path, args.test_fraction)
