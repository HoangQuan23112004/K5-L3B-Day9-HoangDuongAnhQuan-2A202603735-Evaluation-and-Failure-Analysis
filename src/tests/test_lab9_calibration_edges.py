"""M2: failure detection, undefined estimates and calibration decisions."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


def test_helpful_precision_does_not_hide_missed_failures():
    from lab9.judge import calibrate

    result = calibrate(Path("data/eval/judge_helpful_public.csv"))
    assert result["confusion"] == {"tp": 9, "fp": 0, "fn": 21, "tn": 70}
    assert result["precision"] == 1.0
    assert result["recall"] == 0.3
    assert result["kappa"] == 0.375
    assert result["corrected_fail_rate"] == 0.3
    assert result["passed"] is False


def test_tone_passes_calibration():
    from lab9.judge import calibrate

    result = calibrate(Path("data/eval/judge_tone_public.csv"))
    assert result["passed"] is True
    assert result["observed_fail_rate"] == 0.28
    assert result["corrected_fail_rate"] == 0.3


def test_constant_predictions_with_mixed_truth_have_zero_kappa():
    from lab9.stats import cohen_kappa, precision_recall

    assert cohen_kappa(["PASS", "FAIL"], ["PASS", "PASS"]) == 0.0
    assert precision_recall(["PASS", "FAIL"], ["PASS", "PASS"]) == (0.0, 0.0)


@pytest.mark.parametrize("human,judge", [([], []), (["FAIL"], ["FAIL"])])
def test_undefined_kappa(human, judge):
    from lab9.stats import cohen_kappa

    with pytest.raises(ValueError):
        cohen_kappa(human, judge)


@pytest.mark.parametrize("human,judge", [(["PASS"], []), (["OTHER"], ["PASS"])])
def test_confusion_rejects_invalid_inputs(human, judge):
    from lab9.stats import confusion

    with pytest.raises(ValueError):
        confusion(human, judge)


def test_rogan_gladen_upper_clip_and_unidentifiable_judge():
    from lab9.stats import rogan_gladen

    assert rogan_gladen(1.0, 0.8, 0.9) == 1.0
    with pytest.raises(ValueError):
        rogan_gladen(0.5, 0.5, 0.5)
    with pytest.raises(ValueError):
        rogan_gladen(float("nan"), 0.8, 0.9)
