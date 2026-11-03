from types import SimpleNamespace

import numpy as np
import pytest
from scipy.optimize import minimize_scalar
from scipy.stats import multivariate_normal

from microlens.covariance06 import (
    _scale,
    fit_all_practical,
    fit_covariance06,
    gp_covariance,
    scaled_profile,
)
from microlens.inference import Observations


def example():
    t = np.linspace(0, 10, 21)
    y = 1 + 0.6 * np.exp(-0.5 * ((t - 5) / 0.7) ** 2) + 0.02 * np.sin(t * 3)
    return Observations(t, y, np.full(len(t), 0.04))


def test_tiny_and_exact_zero_columns_keep_feasible_linear_solution():
    t = np.arange(8.0)
    design = np.column_stack([t * 1e-250, np.ones(8)])
    y = 0.3 * t + 0.7
    coefficients, nll, q = scaled_profile(design, y, np.eye(8) * 0.1)
    np.testing.assert_allclose(coefficients, [0.3e250, 0.7], rtol=1e-12)
    np.testing.assert_allclose(design @ coefficients, y, atol=1e-12)
    assert q < 1e-20
    assert nll == pytest.approx(
        -multivariate_normal.logpdf(y - design @ coefficients, cov=np.eye(8) * 0.01)
    )
    coefficients, _, _ = scaled_profile(
        np.column_stack([np.zeros(8), np.ones(8)]), np.full(8, 2.0), np.eye(8)
    )
    np.testing.assert_allclose(coefficients, [0, 2])


def test_exact_zero_gp_variance_nested_diagonal():
    obs = example()
    c = gp_covariance(obs, np.log(1.25), 0.0, np.log(12.0))
    np.testing.assert_array_equal(c, np.diag((1.25 * obs.sigma) ** 2))
    with pytest.raises(ValueError, match="nonnegative"):
        gp_covariance(obs, 0.0, -1.0, 0.0)


def test_analytic_scale_profile_against_independent_scalar_search():
    obs = example()
    diagonal = fit_covariance06(obs, mode="diagonal")
    scale = _scale(obs, diagonal)
    for name, d in diagonal["fits"].items():
        q = d["quadratic"]
        objective = lambda s, q=q: 0.5 * q / s**2 + len(obs.t) * np.log(s)
        ref = minimize_scalar(
            objective, bounds=(0.5, 3), method="bounded", options={"xatol": 1e-11}
        )
        selected = scale["fits"][name]
        candidates = [objective(0.5), objective(3.0), ref.fun]
        assert objective(selected["noise"]["sigma_scale"]) == pytest.approx(
            min(candidates), abs=1e-7
        )
        assert selected["parameters"] == d["parameters"]
        assert selected["parameter_count"] == d["parameter_count"] + 1
        assert selected["success"] == d["success"]


def test_practical_api_rejects_privileged_covariance():
    obs = example()
    with pytest.raises(ValueError, match="forbidden"):
        fit_covariance06(obs, known_covariance=np.eye(len(obs.t)))
    with pytest.raises(TypeError):
        fit_all_practical(obs, known_covariance=np.eye(len(obs.t)))
    with pytest.raises(ValueError, match="requires"):
        fit_covariance06(obs, mode="oracle")


def test_worse_converged_endpoint_cannot_hide_better_feasible_point(monkeypatch):
    def fake_minimize(fun, x0, **kwargs):
        bad = np.array(x0, copy=True)
        if len(bad) == 3:
            bad[1], bad[2] = 1.9, np.log(0.001)
        else:
            bad[0], bad[1] = 1.9, np.log(0.001)
        value = fun(bad)
        return SimpleNamespace(
            x=bad, fun=value, success=True, nfev=1, nit=0, message="forced worse endpoint"
        )

    monkeypatch.setattr("microlens.covariance06.minimize", fake_minimize)
    result = fit_covariance06(example(), mode="diagonal")
    fit = result["fits"]["gaussian"]
    assert not fit["success"] and fit["fallback_used"] and not result["valid"]
    assert fit["nll"] < min(s["final_nll"] for s in fit["starts"]) - 10
    assert fit["selected_minus_best_feasible"] <= fit["incumbent_tolerance"]


def test_hard_evaluation_cap_keeps_failure_flag_and_finite_incumbent():
    result = fit_covariance06(example(), mode="diagonal", maxfun=1)
    fit = result["fits"]["gaussian"]
    assert fit["nll"] is not None and not fit["optimizer_success"]
    assert any(s.get("budget_exhausted") for s in fit["starts"])
    assert all(s["likelihood_evaluations"] <= 1 for s in fit["starts"])


def test_joint_fit_retains_exact_scale_only_initial_incumbent():
    obs = example()
    result = fit_all_practical(obs, maxiter=80, maxfun=1000)
    for family, fit in result["estimated"]["fits"].items():
        assert fit["initial_incumbent_nll"] == pytest.approx(
            result["scale"]["fits"][family]["nll"], abs=1e-8
        )
        assert fit["nll"] <= fit["initial_incumbent_nll"] + fit["incumbent_tolerance"]
        assert (
            fit["nll"] <= min(p["nll"] for p in fit["incumbent_trace"]) + fit["incumbent_tolerance"]
        )


def test_oracle_density_uses_only_explicit_known_covariance():
    obs = example()
    distance = abs(obs.t[:, None] - obs.t[None, :])
    c = np.diag(obs.sigma**2) + 0.02**2 * np.exp(-distance / 1.8)
    result = fit_covariance06(obs, mode="oracle", known_covariance=c)
    assert result["oracle_only"]
    for name, fit in result["fits"].items():
        p = fit["parameters"]
        if name == "constant":
            predicted = np.full(len(obs.t), p[0])
        elif name == "gaussian":
            predicted = p[0] + p[1] * np.exp(-((obs.t - p[2]) ** 2) / (2 * p[3] ** 2))
        else:
            u2 = p[0] ** 2 + ((obs.t - p[1]) / p[2]) ** 2
            predicted = p[3] * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + p[4]
        ref = -multivariate_normal.logpdf(obs.flux - predicted, cov=c)
        assert fit["nll"] == pytest.approx(ref, abs=1e-8)
        assert fit["bic"] == pytest.approx(
            2 * ref + {"constant": 1, "pspl": 5, "gaussian": 4}[name] * np.log(len(obs.t))
        )
