"""Controlled covariance/family interventions; generator truth stays outside inference."""

import hashlib

import numpy as np
from scipy.linalg import cholesky
from scipy.optimize import brentq, minimize_scalar

from .covariance import matern32_covariance
from .inference import Observations
from .simulation import generate_pair


def double_bump_profile(x):
    return 0.5 * np.exp(-0.5 * (x - 2) ** 2) + 0.5 * np.exp(-0.5 * (x + 2) ** 2)


_peak_location = minimize_scalar(
    lambda x: -double_bump_profile(x), bounds=(1, 3), method="bounded"
).x
DOUBLE_PEAK = float(double_bump_profile(_peak_location))
DOUBLE_OUTER_HALF = brentq(lambda x: double_bump_profile(x) - DOUBLE_PEAK / 2, 2, 8)


def double_bump_flux(t, center, amplitude, fwhm):
    scale = fwhm / (2 * DOUBLE_OUTER_HALF)
    return 1 + amplitude * double_bump_profile((np.asarray(t) - center) / scale) / DOUBLE_PEAK


def source_views(source, config, phase):
    pair = generate_pair(source, snr=config["snr"], n_observations=config["n_observations"])
    t, true_sigma = pair.views["pspl"]["complete"].t, pair.views["pspl"]["complete"].sigma
    means = dict(pair.truth.clean_means)
    families = config[phase + "_families"]
    if "double_bump" in families:
        means["double_bump"] = double_bump_flux(
            t, pair.truth.pspl_parameters["t0"], pair.truth.amplitude, pair.truth.fwhm_days
        )
    rng = np.random.default_rng(
        int.from_bytes(hashlib.sha256((source.source_id + ":noise").encode()).digest()[:8], "big")
    )
    standard_noise = rng.normal(size=len(t))
    views, specs = [], {}
    for noise in config[phase + "_noise"]:
        amplitude = config["noise_amplitude_over_median_sigma"] * float(np.median(true_sigma))
        length = config["noise_length_days"]
        if noise == "white":
            amplitude = 0.0
            true_c = np.diag(true_sigma**2)
            reported = true_sigma
        elif noise == "matern_biased":
            true_c = matern32_covariance(t, true_sigma, amplitude=amplitude, length=length)
            reported = config["reported_sigma_bias"] * true_sigma
        elif noise == "ou_biased":
            true_c = np.diag(true_sigma**2) + amplitude**2 * np.exp(
                -np.abs(t[:, None] - t[None, :]) / length
            )
            reported = config["reported_sigma_bias"] * true_sigma
        else:
            raise ValueError("unknown generator noise")
        additive = cholesky(true_c, lower=True) @ standard_noise
        specs[noise] = {"amplitude": amplitude, "length_days": length}
        for family in families:
            flux = means[family] + additive
            for condition in config[phase + "_conditions"]:
                mask = pair.truth.masks[condition]
                obs = Observations(t[mask], flux[mask], reported[mask])
                views.append((noise, family, condition, obs, true_c[np.ix_(mask, mask)]))
    truth = {
        "source_id": source.source_id,
        "t": t.tolist(),
        "sigma_true": true_sigma.tolist(),
        "pspl_parameters": pair.truth.pspl_parameters,
        "gaussian_parameters": pair.truth.gaussian_parameters,
        "noise_specs": specs,
        "amplitude": pair.truth.amplitude,
        "fwhm_days": pair.truth.fwhm_days,
    }
    return views, truth
