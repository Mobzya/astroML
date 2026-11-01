"""Point-source point-lens photometry in linear, normalized flux units."""

import numpy as np


def magnification(u):
    """PSPL magnification for finite positive separations in Einstein-radius units."""
    u = np.asarray(u, dtype=float)
    if not np.all(np.isfinite(u)) or np.any(u <= 0):
        raise ValueError("u must be finite and strictly positive")
    # Algebraically equivalent form avoids squaring very large separations.
    return (u / np.hypot(u, 2)) + (2 / u) / np.hypot(u, 2)


def pspl_flux(t, u0, t0, t_e, f_s, f_b):
    """Time and t_e share units (days in this project); f_s, f_b are nonnegative."""
    parameters = np.array([u0, t0, t_e, f_s, f_b], dtype=float)
    t = np.asarray(t, dtype=float)
    if not np.all(np.isfinite(parameters)) or not np.all(np.isfinite(t)):
        raise ValueError("times and parameters must be finite")
    if u0 <= 0 or t_e <= 0 or f_s < 0 or f_b < 0:
        raise ValueError("u0/t_e must be positive and flux components nonnegative")
    return f_s * magnification(np.hypot(u0, (t - t0) / t_e)) + f_b
