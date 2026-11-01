"""Matched synthetic pairs for reconstruction R2, not historical data recovery.

This module is a generator and may access latent truth. Inference receives ONLY
the Observations objects in GeneratedPair.views. The shared-noise Gaussian/PSPL
pair and every masked view form one independent experimental unit.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from .inference import Observations
from .physics import magnification, pspl_flux


@dataclass(frozen=True)
class Source:
    source_id: str
    split: str


def _rng(key):
    digest = hashlib.sha256(key.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "big"))


def source_manifest(namespace: str, seed: int, counts: Mapping[str, int]):
    """Assign pair IDs to exact split counts before generating observations.

    The namespace must be new for an independent experiment. All sources in this
    manifest are distinct latent pairs; two classes in one pair are dependent.
    """
    if (
        not namespace
        or not counts
        or any(
            not name or isinstance(n, bool) or not isinstance(n, int) or n < 0
            for name, n in counts.items()
        )
    ):
        raise ValueError("nonempty namespace/splits and nonnegative integer counts required")
    total = sum(counts.values())
    if total == 0:
        raise ValueError("at least one source required")
    identifiers = [f"{namespace}:{seed}:{i:08d}" for i in range(total)]
    order = _rng(f"{namespace}:{seed}:split-assignment").permutation(total)
    result = []
    cursor = 0
    for split, n in sorted(counts.items()):
        result.extend(Source(identifiers[i], split) for i in order[cursor : cursor + n])
        cursor += n
    return tuple(result)


def pspl_fwhm(u0: float, t_e: float):
    """Exact width at half of the excess over baseline, not half total flux."""
    if not np.isfinite(u0) or not np.isfinite(t_e) or not 0.01 <= u0 <= 3 or t_e <= 0:
        raise ValueError("require 0.01 <= u0 <= 3 and positive finite t_e")
    a_half = (float(magnification(u0)) + 1) / 2
    u_half_squared = 2 * (a_half / np.sqrt(a_half * a_half - 1) - 1)
    return float(2 * t_e * np.sqrt(u_half_squared - u0 * u0))


@dataclass(frozen=True)
class PairTruth:
    """Privileged diagnostic store. Never supply to a fit or a calibrator."""

    pspl_parameters: dict
    gaussian_parameters: dict
    amplitude: float
    fwhm_days: float
    clean_means: dict
    masks: dict


@dataclass(frozen=True)
class GeneratedPair:
    source: Source
    views: dict
    truth: PairTruth


def generate_pair(source: Source, snr: float = 15.0, n_observations: int = 96):
    """Matched amplitudes/FWHM/baselines/times/errors and one shared white-noise draw.

    SNR = analytic peak excess / nominal sigma (heteroskedastic factors .8..1.2).
    Repeated SNR values share latent shape, cadence, standard noise and masks.
    This is a controlled toy population, not a calibrated telescope noise model.
    """
    if not np.isfinite(snr) or snr <= 0 or n_observations < 10:
        raise ValueError("positive finite SNR and at least ten observations required")
    latent = _rng(source.source_id + ":latent")
    p = {
        "u0": latent.uniform(0.15, 1),
        "t0": latent.uniform(60, 180),
        "t_e": np.exp(latent.uniform(np.log(8), np.log(35))),
        "f_s": latent.uniform(0.3, 0.9),
    }
    p["f_b"] = 1 - p["f_s"]
    amplitude = p["f_s"] * (float(magnification(p["u0"])) - 1)
    width = pspl_fwhm(p["u0"], p["t_e"])
    gp = {
        "baseline": 1.0,
        "amplitude": amplitude,
        "center": p["t0"],
        "width": width / (2 * np.sqrt(2 * np.log(2))),
    }
    cadence = _rng(source.source_id + ":cadence")
    t = (np.arange(n_observations) + cadence.uniform(size=n_observations)) * (240 / n_observations)
    noise_rng = _rng(source.source_id + ":noise")
    sigma = (amplitude / snr) * noise_rng.uniform(0.8, 1.2, n_observations)
    noise = noise_rng.normal(size=n_observations) * sigma
    means = {
        "pspl": pspl_flux(t, **p),
        "gaussian": gp["baseline"]
        + gp["amplitude"] * np.exp(-0.5 * ((t - gp["center"]) / gp["width"]) ** 2),
    }
    keep = round(n_observations * 0.6)
    masks = {
        "complete": np.ones(n_observations, bool),
        "random40": np.zeros(n_observations, bool),
        "peak40": np.ones(n_observations, bool),
    }
    masks["random40"][
        _rng(source.source_id + ":mask").choice(n_observations, keep, replace=False)
    ] = True
    # Generator intervention only: detector never receives t0 or a mask label.
    masks["peak40"][np.argsort(abs(t - p["t0"]))[: n_observations - keep]] = False
    views = {
        family: {
            condition: Observations(t[mask], (mean + noise)[mask], sigma[mask])
            for condition, mask in masks.items()
        }
        for family, mean in means.items()
    }
    truth = PairTruth(p, gp, amplitude, width, means, masks)
    return GeneratedPair(source, views, truth)
