"""
Early-warning metrics. NumPy only, so they run anywhere the contract tests run.

These are the numbers that distinguish a forecasting system from a detector. A detector can
score a perfect F1 while warning exactly zero seconds before impact; lead time is what shows
the warning arrived in time to act.
"""

from __future__ import annotations

import numpy as np

WINDOW_SECONDS = 60


def attack_episodes(labels: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous runs of attack windows, as inclusive (first_index, last_index) pairs."""
    episodes: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(labels):
        if value and start is None:
            start = index
        elif not value and start is not None:
            episodes.append((start, index - 1))
            start = None
    if start is not None:
        episodes.append((start, len(labels) - 1))
    return episodes


def lead_time_metrics(
    y_true: np.ndarray, y_score: np.ndarray, threshold: float, window_seconds: int = WINDOW_SECONDS
) -> dict:
    """
    How early the model warns, per attack episode.

    For each episode, walk back through the benign windows immediately before its onset
    while they are already above the threshold. That unbroken run is the warning, and its
    length is the lead time. An episode whose first alarm is the onset window itself scores
    zero. An episode with no alarm at or after onset is a miss.

    ``false_warnings_per_hour`` divides alarms on benign windows by the benign time observed,
    so the lead time can be read against the noise an analyst pays for it.
    """
    y_true = np.asarray(y_true).astype(bool)
    alarms = np.asarray(y_score) >= threshold

    leads: list[int] = []
    missed = 0
    for onset, _ in attack_episodes(y_true):
        if not alarms[onset:].any():
            missed += 1
            continue
        cursor = onset
        while cursor - 1 >= 0 and not y_true[cursor - 1] and alarms[cursor - 1]:
            cursor -= 1
        leads.append((onset - cursor) * window_seconds)

    benign_windows = int((~y_true).sum())
    false_alarms = int((alarms & ~y_true).sum())
    benign_hours = (benign_windows * window_seconds) / 3600 if benign_windows else 0.0
    return {
        "episodes": len(attack_episodes(y_true)),
        "warned_episodes": len(leads),
        "missed_episodes": missed,
        "mean_lead_time_sec": round(float(np.mean(leads)), 1) if leads else None,
        "median_lead_time_sec": round(float(np.median(leads)), 1) if leads else None,
        "max_lead_time_sec": int(max(leads)) if leads else None,
        "false_warnings_per_hour": round(false_alarms / benign_hours, 2) if benign_hours else None,
        "note": "Lead time counts whole windows before attack onset; zero means the alarm and the attack start together.",
    }
