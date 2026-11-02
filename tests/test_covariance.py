import numpy as np
import pytest
from scipy.linalg import cholesky

from microlens.covariance import fit_covariance_models, matern32_covariance, profile_linear
from microlens.inference import Observations, gaussian_nll


def test_matern_spd_duplicates_and_diagonal_limit():
    t = np.array([0.0, 0.0, 1.0, 3.0, 8.0, 20.0])
    sigma = np.array([0.02, 0.03, 0.04, 0.05, 0.06, 0.07])
    np.testing.assert_array_equal(matern32_covariance(t, sigma), np.diag(sigma**2))
    c = matern32_covariance(t, sigma, 1.5, 0.2, 12.0)
    np.testing.assert_allclose(c, c.T)
    np.testing.assert_allclose(np.diag(c), (1.5 * sigma) ** 2 + 0.2**2)
    assert np.min(np.linalg.eigvalsh(c)) > 0


def test_profile_linear_exact_solution_and_density():
    t = np.arange(8.0)
    design = np.column_stack([t, np.ones(8)])
    y = 0.3 * t + 0.7
    c = matern32_covariance(t, np.full(8, 0.1), amplitude=0.2)
    coefficients, nll = profile_linear(design, y, cholesky(c, lower=True))
    np.testing.assert_allclose(coefficients, [0.3, 0.7], atol=1e-12)
    assert nll == pytest.approx(gaussian_nll(y - design @ coefficients, c))
    assert nll <= gaussian_nll(y - design @ np.array([0.4, 0.8]), c)


def test_oracle_guard_and_diagonal_constant():
    t = np.linspace(0, 20, 12)
    obs = Observations(t, np.ones(12), np.full(12, 0.03))
    with pytest.raises(ValueError, match="forbidden"):
        fit_covariance_models(obs, known_covariance=np.eye(12))
    with pytest.raises(ValueError, match="needs"):
        fit_covariance_models(obs, mode="oracle")
    diagonal = fit_covariance_models(obs, mode="diagonal", maxiter=30, maxfun=200)
    assert diagonal["fits"]["constant"]["parameters"][0] == pytest.approx(1)
    assert diagonal["fits"]["constant"]["nll"] == pytest.approx(
        gaussian_nll(np.zeros(12), np.diag(obs.sigma**2))
    )
