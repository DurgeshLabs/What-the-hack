"""
Tests for the early-warning metrics.

Lead time is the project's headline claim, so its edge cases are pinned here: warning
before onset, warning exactly at onset, a complete miss, a broken warning run, and the
false-alarm rate that the lead time costs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.evaluation.lead_time import attack_episodes, lead_time_metrics  # noqa: E402

WINDOW = 60


def scores(*values: float) -> np.ndarray:
    return np.asarray(values, dtype=float)


def labels(*values: int) -> np.ndarray:
    return np.asarray(values, dtype=int)


@pytest.mark.parametrize(
    ("series", "expected"),
    [
        ([0, 0, 0], []),
        ([1, 1, 1], [(0, 2)]),
        ([0, 1, 1, 0], [(1, 2)]),
        ([1, 0, 1], [(0, 0), (2, 2)]),
        ([0, 0, 1], [(2, 2)]),
    ],
)
def test_attack_episodes_finds_contiguous_runs(series, expected) -> None:
    assert attack_episodes(labels(*series)) == expected


def test_warning_before_onset_counts_every_benign_window_it_covers() -> None:
    result = lead_time_metrics(labels(0, 0, 0, 1, 1, 0), scores(0.1, 0.9, 0.9, 0.9, 0.9, 0.1), 0.5)
    assert result["warned_episodes"] == 1
    assert result["missed_episodes"] == 0
    assert result["mean_lead_time_sec"] == 2 * WINDOW


def test_alarm_at_onset_only_is_zero_lead_not_a_miss() -> None:
    result = lead_time_metrics(labels(0, 0, 1, 1), scores(0.1, 0.1, 0.9, 0.9), 0.5)
    assert result["warned_episodes"] == 1
    assert result["missed_episodes"] == 0
    assert result["mean_lead_time_sec"] == 0.0


def test_no_alarm_at_or_after_onset_is_a_miss() -> None:
    result = lead_time_metrics(labels(0, 0, 1, 1), scores(0.9, 0.1, 0.1, 0.1), 0.5)
    assert result["warned_episodes"] == 0
    assert result["missed_episodes"] == 1
    assert result["mean_lead_time_sec"] is None


def test_a_gap_breaks_the_warning_run() -> None:
    # The alarm at index 0 is separated from onset by a quiet window, so only the
    # unbroken run immediately before onset counts.
    result = lead_time_metrics(labels(0, 0, 0, 1), scores(0.9, 0.1, 0.9, 0.9), 0.5)
    assert result["mean_lead_time_sec"] == 1 * WINDOW


def test_multiple_episodes_are_averaged() -> None:
    result = lead_time_metrics(
        labels(0, 0, 1, 0, 0, 0, 1),
        scores(0.9, 0.9, 0.9, 0.1, 0.1, 0.9, 0.9),
        0.5,
    )
    assert result["episodes"] == 2
    assert result["warned_episodes"] == 2
    # First episode warned 2 windows early, second 1 window early.
    assert result["mean_lead_time_sec"] == pytest.approx(1.5 * WINDOW)
    assert result["max_lead_time_sec"] == 2 * WINDOW


def test_false_warnings_per_hour_uses_benign_time_only() -> None:
    # Six benign windows is six minutes; three of them raise an alarm.
    result = lead_time_metrics(
        labels(0, 0, 0, 0, 0, 0, 1),
        scores(0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.9),
        0.5,
    )
    assert result["false_warnings_per_hour"] == pytest.approx(3 / (6 * WINDOW / 3600))


def test_threshold_changes_the_answer() -> None:
    truth, risk = labels(0, 0, 1), scores(0.4, 0.6, 0.9)
    assert lead_time_metrics(truth, risk, 0.5)["mean_lead_time_sec"] == 1 * WINDOW
    assert lead_time_metrics(truth, risk, 0.3)["mean_lead_time_sec"] == 2 * WINDOW
    assert lead_time_metrics(truth, risk, 0.95)["missed_episodes"] == 1


def test_all_benign_reports_no_episodes() -> None:
    result = lead_time_metrics(labels(0, 0, 0), scores(0.1, 0.1, 0.1), 0.5)
    assert result["episodes"] == 0
    assert result["warned_episodes"] == 0
    assert result["mean_lead_time_sec"] is None
    assert result["false_warnings_per_hour"] == 0.0
