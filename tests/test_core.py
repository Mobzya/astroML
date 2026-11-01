import numpy as np
import pytest
from scipy.stats import multivariate_normal

from microlens.inference import Observations, fit_models, gaussian_nll
from microlens.physics import magnification, pspl_flux


def test_physics_limits_and_symmetry():
    assert np.all(magnification([0.01, 0.1, 1, 10]) > 1)
    assert magnification(1e8) == pytest.approx(1)
    assert magnification(0.1) > magnification(0.5)
    assert pspl_flux(-5, 0.2, 0, 20, 0.7, 0.3) == pspl_flux(5, 0.2, 0, 20, 0.7, 0.3)
    assert pspl_flux(10, 0.2, 0, 40, 0.7, 0.3) > pspl_flux(10, 0.2, 0, 20, 0.7, 0.3)
    assert pspl_flux(1e9, 0.2, 0, 20, 0.7, 0.3) == pytest.approx(1)


@pytest.mark.parametrize("u", [0, -1, np.nan, np.inf])
def test_invalid_separation(u):
    with pytest.raises(ValueError):
        magnification(u)


def test_gaussian_likelihood_independent_reference():
    r = np.array([0.2, -0.3, 0.7])
    c = np.array([[2, 0.3, 0], [0.3, 1, 0.2], [0, 0.2, 0.5]])
    assert gaussian_nll(r, c) == pytest.approx(-multivariate_normal.logpdf(r, cov=c))
    s = np.array([0.1, 0.2, 0.3])
    expected = 0.5 * np.sum((r / s) ** 2 + np.log(2 * np.pi * s**2))
    assert gaussian_nll(r, np.diag(s * s)) == pytest.approx(expected)


def test_covariance_rejects_invalid():
    with pytest.raises(np.linalg.LinAlgError):
        gaussian_nll([1, 2], [[1, 1], [1, 1]])
    with pytest.raises(ValueError):
        gaussian_nll([1, 2], [[1, 0.1], [0.2, 1]])


def test_observation_validation_and_copy():
    t = np.arange(10.0)
    obs = Observations(t, np.ones(10), np.ones(10))
    t[0] = 100
    assert obs.t[0] == 0
    with pytest.raises(ValueError):
        Observations(t, np.ones(10), np.zeros(10))


def test_noiseless_pspl_fit_and_constant():
    t = np.linspace(0, 100, 64)
    flux = pspl_flux(t, 0.4, 50, 12, 0.7, 0.3)
    fits = fit_models(Observations(t, flux, np.full(64, 0.03)))
    assert fits["pspl"]["success"]
    assert fits["pspl"]["chi2"] < 1e-8
    assert fits["pspl"]["bic"] < fits["constant"]["bic"]
    flat = fit_models(Observations(t, np.ones(64), np.full(64, 0.03)))
    assert flat["constant"]["chi2"] == pytest.approx(0)
    assert flat["constant"]["bic"] < flat["pspl"]["bic"]


def test_mulensmodel_independent():
    mm = pytest.importorskip("MulensModel")
    t = np.linspace(-100, 100, 101)
    for u0 in (0.01, 0.2, 1.5):
        for te in (3.0, 20.0, 80.0):
            model = mm.Model({"t_0": 0.0, "u_0": u0, "t_E": te})
            ours = pspl_flux(t, u0, 0, te, 1, 0)
            np.testing.assert_allclose(ours, model.get_magnification(t), rtol=1e-12)
