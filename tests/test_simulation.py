import numpy as np
import pytest

from microlens.physics import pspl_flux
from microlens.simulation import generate_pair, pspl_fwhm, source_manifest


def test_matching_with_independent_half_max_check():
    sources = source_manifest("unit-test-only", 32, {"development": 12})
    for source in sources:
        pair = generate_pair(source)
        truth, p = pair.truth, pair.truth.pspl_parameters
        left_right = p["t0"] + np.array([-0.5, 0.5]) * truth.fwhm_days
        half_height = 1 + truth.amplitude / 2
        np.testing.assert_allclose(pspl_flux(left_right, **p), half_height, rtol=1e-11)
        g = truth.gaussian_parameters
        gaussian = g["baseline"] + g["amplitude"] * np.exp(
            -0.5 * ((left_right - g["center"]) / g["width"]) ** 2
        )
        np.testing.assert_allclose(gaussian, half_height, rtol=1e-11)
        assert pspl_flux(p["t0"], **p) == pytest.approx(1 + g["amplitude"])
        for mask in ("complete", "random40", "peak40"):
            a, b = (pair.views[f][mask] for f in ("pspl", "gaussian"))
            np.testing.assert_array_equal(a.t, b.t)
            np.testing.assert_array_equal(a.sigma, b.sigma)
            assert len(a.t) == (96 if mask == "complete" else 58)
        # Same noise is added to the clean matched means; no class-specific sigma.
        for family in ("pspl", "gaussian"):
            residual = pair.views[family]["complete"].flux - truth.clean_means[family]
            if family == "pspl":
                reference = residual
            else:
                np.testing.assert_allclose(residual, reference, atol=5e-16)


def test_source_disjoint_splits_and_reproducibility():
    counts = {"train": 10, "calibration": 5, "evaluation": 7}
    first = source_manifest("unit-test-only", 1, counts)
    assert first == source_manifest("unit-test-only", 1, counts)
    ids = [s.source_id for s in first]
    assert len(set(ids)) == len(ids)
    for split, count in counts.items():
        assert sum(s.split == split for s in first) == count
    second = source_manifest("independent-namespace", 1, counts)
    assert set(ids).isdisjoint(s.source_id for s in second)
    a, b = generate_pair(first[0]), generate_pair(first[0])
    np.testing.assert_array_equal(
        a.views["pspl"]["complete"].flux, b.views["pspl"]["complete"].flux
    )


def test_masks_are_shared_between_snr_views_and_truth_is_separate():
    source = source_manifest("unit-test-only", 40, {"development": 1})[0]
    a, b = generate_pair(source, snr=5), generate_pair(source, snr=50)
    for mask in a.truth.masks:
        np.testing.assert_array_equal(a.truth.masks[mask], b.truth.masks[mask])
        obs = a.views["pspl"][mask]
        assert set(vars(obs)) == {"t", "flux", "sigma"}
    with pytest.raises(ValueError):
        generate_pair(source, snr=0)
    with pytest.raises(ValueError):
        source_manifest("x", 0, {"development": -1})
    with pytest.raises(ValueError):
        pspl_fwhm(0, 10)
