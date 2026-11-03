"""The independent active-set verifier must also retain tiny nonzero columns."""

import importlib
from pathlib import Path

import numpy as np


def test_reference_profile_tiny_column(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    reference = importlib.import_module("verify_covariance06")
    t = np.linspace(0, 1, 10)
    y = np.ones(10)
    y[-1] = 2
    nll = reference.profiled_nll(t, y, "gaussian", [1.35, np.log(0.01)], np.eye(10))
    np.testing.assert_allclose(nll, 5 * np.log(2 * np.pi), atol=1e-12)
