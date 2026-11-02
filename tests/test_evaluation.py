import numpy as np
import pytest

from microlens.evaluation import (
    auc_from_pairs,
    binomial_interval,
    calibration_threshold,
    decision_metrics,
)


def test_auc_against_pair_comparisons_including_failures_and_ties():
    p, n = np.array([1.0, 2.0, -np.inf]), np.array([1.0, -np.inf, -1.0])
    brute = np.mean((p[:, None] > n).astype(float) + 0.5 * (p[:, None] == n))
    assert auc_from_pairs(p, n) == pytest.approx(brute)
    assert auc_from_pairs([1, 1], [1, 1]) == 0.5
    assert auc_from_pairs([2, 3], [0, 1]) == 1.0


def test_calibration_ties_conservative_and_zero_fp_bound():
    scores = np.r_[np.arange(230), np.full(10, 500.0)]
    threshold = calibration_threshold(scores)
    assert np.count_nonzero(scores >= threshold) <= 12
    assert calibration_threshold(np.full(10, -np.inf)) is None
    ci = binomial_interval(0, 100)
    assert ci[0] == 0
    assert ci[1] == pytest.approx(1 - 0.025**0.01)


def test_reject_denominators_and_empty_acceptance():
    m = decision_metrics([2, -1, 2], [2, -1, 2], [1, 1, 0], [1, 0, 0], 0)
    assert m["fp"] == 1 and m["tp"] == 1
    assert m["fpr_all"] == pytest.approx(1 / 3)
    assert m["fpr_accepted_negative"] == 1
    assert m["recall_all"] == pytest.approx(1 / 3)
    assert m["coverage"] == 0.5
    assert m["selective_risk"] == pytest.approx(2 / 3)
    empty = decision_metrics([1], [1], [0], [0], 0)
    assert empty["selective_risk"] is None and empty["fdr_balanced"] is None
