"""Calibrated-model acceptance gates for synthetic exposure experiments.

The gate rejects predictions that are non-finite, out of bounds, or demonstrably
worse than a constant baseline. It does NOT imply business-domain validation.
"""
from __future__ import annotations

from math import isfinite
from statistics import mean


def brier_score(predictions: list[float], outcomes: list[int]) -> float:
    if len(predictions) != len(outcomes) or not predictions:
        raise ValueError("Equal nonempty series are required")
    if any(not isfinite(p) or not 0 <= p <= 1 for p in predictions):
        raise ValueError("Predictions must be finite probabilities")
    if any(y not in (0, 1) for y in outcomes):
        raise ValueError("Outcomes must be binary")
    return mean((p - y) ** 2 for p, y in zip(predictions, outcomes))


def calibration_report(predictions: list[float], outcomes: list[int]) -> dict:
    """Compute Brier score and fixed-width calibration bins."""
    actual = brier_score(predictions, outcomes)
    baseline = mean(outcomes)
    baseline_score = brier_score([baseline] * len(outcomes), outcomes)
    bins = []
    for index in range(10):
        members = [
            (prediction, outcome)
            for prediction, outcome in zip(predictions, outcomes)
            if min(int(prediction * 10), 9) == index
        ]
        if members:
            bins.append({
                "bin": index,
                "count": len(members),
                "predicted_mean": round(mean(x for x, _ in members), 5),
                "observed_rate": round(mean(y for _, y in members), 5),
            })
    return {
        "samples": len(outcomes),
        "brier_score": round(actual, 6),
        "baseline_brier_score": round(baseline_score, 6),
        "beats_constant_baseline": actual < baseline_score,
        "calibration_bins": bins,
        "notice": "Requires independent historical validation and monitoring",
    }
