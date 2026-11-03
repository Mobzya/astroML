"""Deterministic statistical fixtures independent of any event evaluation."""

import importlib
from pathlib import Path

import numpy as np


def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("covariance06_statistics")


def test_grouped_ties_auc_and_ap(monkeypatch):
    s = stats(monkeypatch)
    tied = s.ranking([1, 1], [1, 1])
    assert tied["raw_auc"] == 0.5 and tied["empirical_average_precision"] == 0.5
    good = s.ranking([3, 2], [1, 0])
    assert good["raw_auc"] == 1 and good["empirical_average_precision"] == 1
    reversed = s.ranking([0, 0], [1, 1])
    assert reversed["raw_auc"] == 0 and reversed["empirical_average_precision"] == 0.5


def test_empirical_threshold_ties_invalid_and_exact_intervals(monkeypatch):
    s = stats(monkeypatch)
    assert s.threshold([-np.inf] * 20) is None
    assert s.threshold([1] * 20) > 1
    assert s.threshold(range(20)) == np.nextafter(18, np.inf)
    lo, hi = s.cp(0, 240)
    assert lo == 0 and abs(hi - (1 - 0.025 ** (1 / 240))) < 1e-12
    lo, hi = s.cp(240, 240)
    assert hi == 1 and abs(lo - 0.025 ** (1 / 240)) < 1e-12


def test_stratified_bootstrap_keeps_source_units(monkeypatch):
    s = stats(monkeypatch)
    records = [{"seed": 1}] * 3 + [{"seed": 2}] * 4
    draw = s.stratum_draw(np.random.default_rng(2), records, [1, 2])
    assert len(draw) == 7
    assert sum(i < 3 for i in draw) == 3 and sum(i >= 3 for i in draw) == 4
