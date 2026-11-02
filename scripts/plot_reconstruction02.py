"""Plot saved R2 metrics only; no fitting, threshold selection or data generation."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("Preserve existing figure; use another path")
    result = json.loads(args.summary.read_text())
    conditions = ["complete", "random40", "peak40"]
    metrics = [result["conditions"][c] for c in conditions]
    labels = ["Полная: 96 точек", "Случайная потеря: 58", "Потеря пика: 58"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    x = np.arange(3)
    aucs = np.array([m["auc"] for m in metrics])
    ci = np.array([m["auc_ci95_pair_bootstrap"] for m in metrics])
    axes[0].errorbar(
        x,
        aucs,
        yerr=np.array([aucs - ci[:, 0], ci[:, 1] - aucs]),
        fmt="o",
        capsize=5,
        color="#1966a0",
    )
    axes[0].axhline(0.5, linestyle=":", color="gray")
    axes[0].set(
        xticks=x,
        xticklabels=labels,
        ylabel="ROC-AUC и парный 95% интервал",
        ylim=(0, 1.04),
        title="Ранжирование при фиксированном бюджете fit",
    )
    for name, label, color in [
        ("fpr_all", "FPR по всем negative", "#b64646"),
        ("recall_all", "Recall по всем positive", "#1966a0"),
        ("coverage", "Доля автоматических решений", "#2e8256"),
    ]:
        axes[1].plot(x, [m[name] for m in metrics], "o-", label=label, color=color)
    axes[1].axhline(0.05, linestyle=":", color="#b64646", label="Calibration target 5%")
    axes[1].set(
        xticks=x,
        xticklabels=labels,
        ylim=(0, 1.04),
        ylabel="Доля",
        title="Один заранее замороженный порог",
    )
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
        ax.tick_params(axis="x", labelsize=8)
    fig.suptitle(
        f"Новая controlled simulation, SNR15, {result['pairs']} evaluation-пар; не survey performance"
    )
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
