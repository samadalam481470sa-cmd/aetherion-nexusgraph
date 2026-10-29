import pytest

from nexusgraph.model_quality import brier_score, calibration_report


def test_strong_model_beats_baseline():
    report = calibration_report([.05, .15, .9, .85], [0, 0, 1, 1])
    assert report["beats_constant_baseline"]
    assert report["samples"] == 4


@pytest.mark.parametrize("probs,targets", [
    ([], []),
    ([.5], [0, 1]),
    ([float("nan")], [1]),
    ([-.1], [0]),
    ([1.1], [1]),
    ([.5], [2]),
])
def test_invalid_samples(probs, targets):
    with pytest.raises(ValueError):
        brier_score(probs, targets)
