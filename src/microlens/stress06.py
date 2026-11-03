"""Predeclared controlled stress generators; all labels/latent values stay here."""

import hashlib

import numpy as np
from scipy.linalg import cholesky

from .cov_simulation import double_bump_flux
from .covariance import matern32_covariance
from .inference import Observations
from .simulation import generate_pair


def alternative_mean(t, family, center, amplitude, fwhm):
    t = np.asarray(t)
    if family == "noise_only":
        return np.ones_like(t, dtype=float)
    if family == "double_bump":
        return double_bump_flux(t, center, amplitude, fwhm)
    if family == "flare":
        tau = fwhm / (5 * np.log(2))
        exponent = np.where(t <= center, (t - center) / tau, -(t - center) / (4 * tau))
        return 1 + amplitude * np.exp(exponent)
    width = fwhm / (2 * np.sqrt(2 * np.log(2)))
    profile = np.exp(-0.5 * ((t - center) / width) ** 2)
    if family == "gaussian":
        return 1 + amplitude * profile
    if family == "eclipse_like":
        return 1 - min(amplitude, 0.8) * profile
    raise ValueError("Unknown frozen alternative")


def stress_views(source, config):
    standard = np.random.default_rng(
        int.from_bytes(
            hashlib.sha256((source.source_id + ":stress-noise").encode()).digest()[:8], "big"
        )
    ).normal(size=config["n_observations"])
    views, cells = [], {}
    for cell in config["cells"]:
        pair = generate_pair(source, cell["snr"], config["n_observations"])
        full = pair.views["pspl"]["complete"]
        t, sigma = full.t, full.sigma
        amp = config["noise_amplitude_over_median_sigma"] * np.median(sigma)
        if cell["noise"] == "white":
            cov, reported = np.diag(sigma**2), sigma
            amp = 0.0
        elif cell["noise"] == "matern_biased":
            cov = matern32_covariance(t, sigma, amplitude=amp, length=cell["ell"])
            reported = config["reported_sigma_bias"] * sigma
        elif cell["noise"] == "ou_biased":
            cov = np.diag(sigma**2) + amp**2 * np.exp(-abs(t[:, None] - t[None, :]) / cell["ell"])
            reported = config["reported_sigma_bias"] * sigma
        else:
            raise ValueError("Unknown stress kernel")
        mask = pair.truth.masks[cell["condition"]]
        extra = alternative_mean(
            t,
            cell["negative"],
            pair.truth.pspl_parameters["t0"],
            pair.truth.amplitude,
            pair.truth.fwhm_days,
        )
        additive = cholesky(cov, lower=True) @ standard
        for family, mean in [("pspl", pair.truth.clean_means["pspl"]), (cell["negative"], extra)]:
            obs = Observations(t[mask], (mean + additive)[mask], reported[mask])
            views.append((cell["id"], family, cell["condition"], obs, cov[np.ix_(mask, mask)]))
        cells[cell["id"]] = {
            "noise": cell["noise"],
            "ell": cell["ell"],
            "snr": cell["snr"],
            "amplitude": float(amp),
            "sigma_true": sigma.tolist(),
            "mask_indices": np.flatnonzero(mask).tolist(),
        }
    return views, {
        "source_id": source.source_id,
        "t": t.tolist(),
        "cells": cells,
        "pspl_parameters": pair.truth.pspl_parameters,
        "gaussian_parameters": pair.truth.gaussian_parameters,
        "amplitude": pair.truth.amplitude,
        "fwhm_days": pair.truth.fwhm_days,
    }
