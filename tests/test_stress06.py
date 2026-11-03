"""Deterministic mechanical gates, never a stress performance benchmark."""

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import cholesky, solve_triangular

from microlens.simulation import Source, source_manifest
from microlens.stress06 import alternative_mean, stress_views


def assert_flare_fixture(mean):
    w, h, c = 10.0, 2.0, 40.0
    np.testing.assert_allclose(
        mean(np.array([c - w / 5, c, c + 4 * w / 5]), "flare", c, h, w), [2, 3, 2]
    )


def test_analytic_shapes_and_corruption_controls():
    assert_flare_fixture(alternative_mean)
    for multiplier in [0.5, -1.0]:
        with pytest.raises(AssertionError):
            assert_flare_fixture(lambda t, f, c, h, w, m=multiplier: alternative_mean(t, f, c, h, w * m))
    t = np.array([35.0, 40.0, 45.0])
    np.testing.assert_allclose(alternative_mean(t, "gaussian", 40, 2, 10), [2, 3, 2])
    np.testing.assert_allclose(alternative_mean(t, "eclipse_like", 40, 2, 10), [0.6, 0.2, 0.6])
    np.testing.assert_allclose(alternative_mean(t, "noise_only", 40, 2, 10), 1)
    assert (
        np.min(alternative_mean(np.linspace(0, 80, 101), "eclipse_like", 40, 200, 10))
        >= 0.2 - 1e-15
    )


def test_counterfactuals_covariance_and_disjoint_manifest():
    cfg = json.loads(Path("configs/cov06_stress.json").read_text())
    # A named deterministic fixture, not any stress/main source.
    views, truth = stress_views(Source("astroml-cov06-fixture-v1:mechanical:0", "development"), cfg)
    assert len(views) == 12
    for i, cell in enumerate(cfg["cells"]):
        a, b = views[2 * i : 2 * i + 2]
        ta, ya, sa = a[3].t, a[3].flux, a[3].sigma
        np.testing.assert_array_equal(ta, b[3].t)
        np.testing.assert_array_equal(sa, b[3].sigma)
        np.testing.assert_allclose(a[4], b[4], atol=0, rtol=0)
        assert len(ta) == (96 if cell["condition"] == "complete" else 58)
        cholesky(a[4], lower=True)
        idx = truth["cells"][cell["id"]]["mask_indices"]
        np.testing.assert_array_equal(np.array(truth["t"])[idx], ta)
        p = truth["pspl_parameters"]
        u2 = p["u0"] ** 2 + ((ta - p["t0"]) / p["t_e"]) ** 2
        mean = p["f_s"] * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + p["f_b"]
        negative = alternative_mean(
            ta, cell["negative"], p["t0"], truth["amplitude"], truth["fwhm_days"]
        )
        np.testing.assert_allclose(ya - mean, b[3].flux - negative, atol=1e-13)
        true_sigma = np.array(truth["cells"][cell["id"]]["sigma_true"])[idx]
        amp = truth["cells"][cell["id"]]["amplitude"]
        np.testing.assert_allclose(np.diag(a[4]), true_sigma**2 + amp**2)
        if cell["condition"] == "complete":
            z = solve_triangular(cholesky(a[4], lower=True), ya - mean, lower=True)
            if i == 0:
                reference = z
            else:
                np.testing.assert_allclose(z, reference, atol=1e-12)
    main = json.loads(Path("configs/experiment_06.json").read_text())
    main_ids = {
        s.source_id
        for s in source_manifest(
            main["namespace"], main["seeds"][0], main["source_counts_per_seed"]
        )
    }
    stress_ids = {
        s.source_id for s in source_manifest(cfg["namespace"], cfg["seeds"][0], {"stress": 80})
    }
    assert main_ids.isdisjoint(stress_ids)
    assert len(stress_ids) == 80
    with pytest.raises(AssertionError):
        assert main_ids.isdisjoint(main_ids)  # deliberately wrong namespace control
