"""Independently recompute saved diagonal scores and validate file checksums."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.run / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        if hashlib.sha256((args.run / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"checksum mismatch: {name}")
    data = np.loadtxt(args.run / "observations.csv", delimiter=",", skiprows=1)
    masks = np.loadtxt(args.run / "masks.csv", delimiter=",", skiprows=1).astype(bool)
    if masks.shape != (96, 3) or list(masks.sum(axis=0)) != [96, 58, 58]:
        raise ValueError("unexpected observation budget")
    results = json.loads((args.run / "fits.json").read_text())
    maximum = 0.0
    for index, name in enumerate(("complete", "random40", "peak40")):
        t, y, sigma = data[masks[:, index]].T
        for model, fit in results[name].items():
            p = fit["parameters"]
            if model == "constant":
                prediction = np.full_like(y, p[0])
            elif model == "gaussian":
                b, a, center, width = p
                prediction = b + a * np.exp(-((t - center) ** 2) / (2 * width**2))
            else:
                u0, t0, te, fs, fb = p
                u2 = u0 * u0 + ((t - t0) / te) ** 2
                prediction = fs * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + fb
            chi2 = np.sum(((y - prediction) / sigma) ** 2)
            bic = chi2 + np.log(2 * np.pi * sigma**2).sum() + len(p) * np.log(len(t))
            for key, value in [("chi2", chi2), ("bic", bic)]:
                maximum = max(maximum, abs(value - fit[key]))
                if not np.isclose(value, fit[key], rtol=1e-10, atol=1e-9):
                    raise ValueError(f"{name}/{model}/{key} mismatch")
    print(json.dumps({"status": "PASS", "fit_rows": 9, "max_absolute_difference": maximum}))


if __name__ == "__main__":
    main()
