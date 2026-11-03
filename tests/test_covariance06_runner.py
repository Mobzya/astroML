"""Logging/encoding must preserve the frozen numerical decisions."""

import importlib.util
from pathlib import Path

import numpy as np

from microlens.covariance import fit_covariance_models
from microlens.covariance06 import fit_all_practical
from microlens.inference import Observations

_spec = importlib.util.spec_from_file_location("cov06_runner", Path("scripts/run_covariance06.py"))
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def test_legacy_logging_delegates_identical_requests_and_decisions():
    t = np.linspace(0, 40, 20)
    obs = Observations(t, 1 + 0.4 * np.exp(-0.5 * ((t - 17) / 4) ** 2), np.full(20, 0.03))
    a = fit_covariance_models(obs, mode="estimated", maxiter=8, maxfun=100)
    b = runner.legacy_logged(obs, 8, 100)
    assert a["score"] == b["score"] and a["valid"] == b["valid"]
    for family in a["fits"]:
        x, y = a["fits"][family], b["fits"][family]
        for key in ["parameters", "noise", "nll", "bic", "success", "numerical_failures"]:
            assert x[key] == y[key]
        for s, r in zip(x["starts"], y["starts"]):
            assert s["nfev"] == r["nfev"] == r["actual_objective_calls"]
            assert s["nll"] == r["final_nll"]
            assert r["initial_nll"] is not None


def test_witness_encoding_keeps_every_scalar_improvement_and_decision():
    obs = Observations(np.linspace(0, 20, 20), np.ones(20), np.full(20, 0.1))
    methods = fit_all_practical(obs, maxiter=4, maxfun=50)
    for method in methods.values():
        encoded = runner.compact(method)
        assert encoded["score"] == method["score"] and encoded["valid"] == method["valid"]
        for family, fit in method["fits"].items():
            if "incumbent_trace" in fit:
                out = encoded["fits"][family]
                assert out["incumbent_nll_history"] == [p["nll"] for p in fit["incumbent_trace"]]
                assert out["incumbent_witnesses"][0] == fit["incumbent_trace"][0]
                assert out["incumbent_witnesses"][-1] == fit["incumbent_trace"][-1]
