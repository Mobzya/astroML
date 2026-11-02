import json
from pathlib import Path

import numpy as np
import pytest

from microlens.cov_simulation import (
    DOUBLE_OUTER_HALF,
    DOUBLE_PEAK,
    double_bump_flux,
    double_bump_profile,
    source_views,
)
from microlens.simulation import source_manifest


def test_double_bump_matching_and_covariance_view_isolation():
    width, amplitude, center = 20.0, 0.7, 100.0
    outer = center + np.array([-0.5, 0.5]) * width
    np.testing.assert_allclose(double_bump_flux(outer, center, amplitude, width), 1 + amplitude / 2)
    assert double_bump_profile(DOUBLE_OUTER_HALF) == pytest.approx(DOUBLE_PEAK / 2)
    cfg = json.loads(Path("configs/experiment_05.json").read_text())
    source = source_manifest("unit-test-cov-only", 1, {"evaluation": 1})[0]
    views, truth = source_views(source, cfg, "evaluation")
    assert len(views) == 27
    for _, _, _, obs, c in views:
        assert set(vars(obs)) == {"t", "flux", "sigma"}
        assert c.shape == (len(obs.t), len(obs.t))
        assert np.min(np.linalg.eigvalsh(c)) > 0
    for noise in cfg["evaluation_noise"]:
        for condition in cfg["evaluation_conditions"]:
            selected = [v[3] for v in views if v[0] == noise and v[2] == condition]
            for obs in selected[1:]:
                np.testing.assert_array_equal(obs.t, selected[0].t)
                np.testing.assert_array_equal(obs.sigma, selected[0].sigma)
    assert truth["source_id"] == source.source_id
