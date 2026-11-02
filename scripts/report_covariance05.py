"""Build figures, complete tables and numerical diagnostics from saved COV05 only."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from analyze_reconstruction02 import load_records


def pct(value):
    return f"{100 * value:.2f}%"


def numerical_diagnostics(records):
    diagnostics = {}
    for mode in ["diagonal", "oracle", "estimated"]:
        methods = [v["results"][mode] for r in records for v in r["views"]]
        fits = [fit for m in methods for fit in m["fits"].values()]
        noises = [f["noise"] for f in fits if f.get("noise")]
        diagnostics[mode] = {
            "method_sets": len(methods),
            "invalid_method_sets": sum(not m["valid"] for m in methods),
            "fit_rows": len(fits),
            "unavailable_fits": sum(f["bic"] is None for f in fits),
            "nonconverged_selected_fits": sum(not f["success"] for f in fits),
            "failed_starts": sum(not s["success"] for f in fits for s in f["starts"]),
            "objective_numerical_failures": sum(len(f["numerical_failures"]) for f in fits),
            "nfev_all_starts": sum(s["nfev"] for f in fits for s in f["starts"]),
            "sum_elapsed_seconds_across_workers": sum(m["runtime_seconds"] for m in methods),
            "maximum_covariance_condition": max(f.get("covariance_condition", 0) for f in fits),
        }
        if noises:
            bound_counts = {}
            for label, lo, hi, get in [
                ("sigma_scale", 0.5, 3.0, lambda n: n["sigma_scale"]),
                ("length_days", 1.0, 120.0, lambda n: n["length_days"]),
            ]:
                v = np.array([get(n) for n in noises])
                bound_counts[label] = {
                    "at_lower": int(np.isclose(v, lo, rtol=1e-5).sum()),
                    "at_upper": int(np.isclose(v, hi, rtol=1e-5).sum()),
                    "total": len(v),
                }
            # Relative amplitude is defined with the view's reported sigma.
            rel = [
                f["noise"]["gp_amplitude"] / np.median(v["sigma"])
                for r in records
                for v in r["views"]
                for f in v["results"][mode]["fits"].values()
                if f.get("noise")
            ]
            bound_counts["amplitude_relative"] = {
                "at_lower": int(np.isclose(rel, 1e-4, rtol=1e-5).sum()),
                "at_upper": int(np.isclose(rel, 4.0, rtol=1e-5).sum()),
                "total": len(rel),
            }
            diagnostics[mode]["noise_bound_counts"] = bound_counts
    return diagnostics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    root = Path("reports/covariance05")
    manifest, records = load_records(args.run)
    diagnostics = numerical_diagnostics(records)
    if manifest["phase"] == "calibration":
        (root / "calibration_diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
        print(json.dumps(diagnostics, indent=2))
        return
    summary = json.loads((root / "evaluation_summary.json").read_text())
    policy = json.loads((root / "frozen_policy.json").read_text())
    (root / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    modes = ["diagonal", "oracle", "estimated"]
    colors = ["#3266ad", "#878787", "#c76328"]
    noises = ["white", "matern_biased", "ou_biased"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    x = np.arange(3)
    for mode, color in zip(modes, colors):
        for ax, metric, negative in [
            (axes[0, 0], "fpr_all", "gaussian"),
            (axes[0, 1], "recall_all", "gaussian"),
            (axes[1, 0], "fpr_all", "double_bump"),
        ]:
            rows = [summary["scenarios"][f"{n}/complete/{negative}"][mode] for n in noises]
            y = np.array([r[metric] for r in rows]) * 100
            ci = np.array([r[metric + "_ci95"] for r in rows]).T * 100
            offset = (modes.index(mode) - 1) * 0.15
            ax.errorbar(
                x + offset,
                y,
                yerr=[y - ci[0], ci[1] - y],
                fmt="o-",
                color=color,
                label=mode,
                capsize=3,
                markersize=4,
            )
        rows = [
            summary["scenarios"][f"ou_biased/{c}/gaussian"][mode]
            for c in ["complete", "random40", "peak40"]
        ]
        axes[1, 1].plot(x, [100 * r["recall_all"] for r in rows], "o-", color=color, label=mode)
    for ax, title in zip(
        axes.flat,
        [
            "Gaussian negatives: FPR, complete",
            "PSPL: recall, complete",
            "Double-bump negatives: FPR, complete",
            "PSPL: recall, OU noise / missingness",
        ],
    ):
        ax.set_title(title)
        ax.set_ylabel("Percent")
        ax.grid(alpha=0.2)
        ax.set_xticks(x, ["white", "Matérn + bias", "OU + bias"])
        ax.legend(fontsize=8)
    axes[0, 0].axhline(5, color="black", linestyle=":", linewidth=1)
    axes[1, 1].set_xticks(x, ["complete", "random40", "peak40"])
    fig.suptitle(
        "COV05: frozen per-method thresholds; 360 independent sources\n"
        "Oracle is privileged; intervals conditional on the frozen policy"
    )
    figure = Path("reports/figures/covariance05_metrics.png")
    fig.savefig(figure, dpi=160)
    plt.close(fig)
    primary = summary["primary"]
    scenario = summary["scenarios"][primary["scenario"]]
    lines = [
        "# COV05: covariance-aware fitting — 02.11.2026",
        "",
        (
            "Новый заранее заданный опыт:240 calibration и360 independent evaluation sources,3 seeds. "
            "Calibration white/Matérn, evaluation дополнительно OU и double bump; "
            "SNR15,96/58 точек. Это toy simulation, не телескопная проверка."
        ),
        "",
        "## Primary outcome",
        "",
        (
            f"Scenario `{primary['scenario']}`, estimated−diagonal. "
            f"ΔFPR={primary['delta_fpr']:.6f},95%CI{primary['delta_fpr_ci95_joint_bootstrap']}; "
            f"Δrecall={primary['delta_recall']:.6f},95%CI{primary['delta_recall_ci95_joint_bootstrap']}."
        ),
        "",
        (
            f"Заранее заданный совместный критерий поддержан: **{primary['full_success_criterion_supported']}**. "
            "Требования: upper CI ΔFPR<0, lower CI Δrecall≥−.05, estimated coverage≥.80. "
            "500 seed-stratified paired source bootstrap draws отдельно resample calibration и evaluation; "
            "порог пересчитан внутри каждого bootstrap. Views одного source сохраняются вместе."
        ),
        "",
        "| Method | FP/360 | FPR | TP/360 | Recall | Coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode in modes:
        r = scenario[mode]
        lines.append(
            f"| {mode} | {r['fp']} | {pct(r['fpr_all'])} | {r['tp']} | "
            f"{pct(r['recall_all'])} | {pct(r['coverage'])} |"
        )
    lines += [
        "",
        (
            "Oracle получает true covariance только в отдельной ветви. Practical estimated "
            "получает только t/flux/reported sigma; truth не передаётся. "
            "Метод/пороги после evaluation не изменены."
        ),
        "",
        "## Все заранее заданные scenarios",
        "",
        (
            "В каждой строке360 independent positives и360 negatives. PSPL повторяется при смене "
            "negative family; строки нельзя складывать как независимые. CI ниже — conditional "
            "Clopper–Pearson95%; secondary contrasts описательные, без simultaneous control."
        ),
        "",
        "| Noise / mask / negative | Method | FP | FPR [95%CI] | TP | Recall [95%CI] | Coverage | AUC |",
        "|---|---|---:|---|---:|---|---:|---:|",
    ]
    for key, methods in summary["scenarios"].items():
        for mode, r in methods.items():
            fci, tci = r["fpr_all_ci95"], r["recall_all_ci95"]
            lines.append(
                f"| {key} | {mode} | {r['fp']} | {pct(r['fpr_all'])} "
                f"[{pct(fci[0])};{pct(fci[1])}] | {r['tp']} | {pct(r['recall_all'])} "
                f"[{pct(tci[0])};{pct(tci[1])}] | {pct(r['coverage'])} | {r['auc']:.4f} |"
            )
    lines += [
        "",
        "![COV05 results](figures/covariance05_metrics.png)",
        "",
        "## Численные отказы, бюджет и воспроизводимость",
        "",
        (
            f"Evaluation elapsed {manifest['runtime_seconds_accumulated']:.2f}s,4 CPU workers,"
            f"1 BLAS thread; maximum per-worker RSS {summary['maximum_worker_rss_kib']}KiB."
        ),
        "",
        "| Method | Sets | Invalid sets | Nonconverged fits | Numerical objective failures | Σ elapsed across workers (s) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode, d in diagnostics.items():
        lines.append(
            f"| {mode} | {d['method_sets']} | {d['invalid_method_sets']} | "
            f"{d['nonconverged_selected_fits']} | {d['objective_numerical_failures']} | "
            f"{d['sum_elapsed_seconds_across_workers']:.1f} |"
        )
    lines += [
        "",
        (
            "Диагностика всех starts/nfev/covariance conditions и попаданий noise-параметров "
            "на bounds: [diagnostics](covariance05/diagnostics.json). Невалидные решения отвергаются; "
            "recall/FPR имеют полные знаменатели. Raw AUC использует best finite score и остаётся "
            "диагностикой, а не performance принятого subset."
        ),
        "",
        (
            "Первая calibration остановилась на48 источниках из-за inf Gaussian NNLS coefficient "
            "при finite residual norm. [Неудачная попытка и hashes](checks/cov05_failed_calibration.json) "
            "сохранены. До evaluation введён finite-coefficient guard и regression test; calibration "
            "целиком выполнена заново. Bounds/starts/пороговый протокол не подбирались по evaluation."
        ),
        "",
        (
            f"Thresholds: `{json.dumps(policy['thresholds'])}`. Каждый выбран на480 dependent "
            "negative views из240 sources; это empirical5%, не distribution-free гарантия. "
            "Freeze commit и точные команды записаны в [freeze](covariance05/calibration_freeze.md)."
        ),
        "",
        (
            "[Protocol](../research/experiment_05_protocol.md), "
            "[config](../configs/experiment_05.json), "
            "[summary/all bootstrap draws/per-seed](covariance05/evaluation_summary.json), "
            "[raw artifacts/SHA256](covariance05/artifacts.json), "
            "[independent verifier](checks/cov05_evaluation_verifier.json)."
        ),
        "",
        "## Границы вывода",
        "",
        (
            "Один SNR, finite optimizer budget, три toy negative/noise families и только3 seeds. "
            "GP гиперпараметры оптимизированы, не маргинализированы; BIC heuristic при bounds и "
            "неидентифицируемости. Возможны локальные минимумы и signal absorption; причинный вклад "
            "каждого механизма отдельно не измерен. Реальные переменные звёзды/артефакты и survey "
            "prevalence не представлены; balanced FDR не оценивает telescope contamination. "
            "Никакая PSPL-классификация не доказывает чёрную дыру. Отрицательный outcome не означает "
            "невозможности любого covariance-aware метода; положительный не переносится за популяцию."
        ),
        "",
    ]
    lines += [
        "",
        (
            "R2 и COV05 имеют разные namespaces и fitting engines/budgets: "
            "R2 использует9 nonlinear starts, COV05 —3 starts с профилированием linear "
            "coefficients. Поэтому сравнение разных опытов не изолирует пользу GP; "
            "primary comparison проводится внутри COV05 на одинаковых sources. "
            "Суммы внутренних elapsed timers не являются CPU-time или изолированным "
            "randomized runtime benchmark. [Среда](covariance05/execution_environment.json)."
        ),
        "",
    ]
    local_path = root / "evaluation_local_minima.json"
    if local_path.exists():
        local = json.loads(local_path.read_text())
        lines += [
            "",
            "## Exploratory oracle-контроль локальных минимумов",
            "",
            (
                "Контроль добавлен после freeze без изменения детектора. True parameters "
                "задают допустимую точку correct mean; estimated использует допустимый "
                "Matérn candidate даже для OU data. Если selected NLL больше candidate "
                "на>1e−5, пропущено допустимое улучшение. Это нижняя оценка числа "
                "локальных провалов, не practical truth-based алгоритм и не новый primary endpoint."
            ),
            "",
            "Primary OU/complete; для каждого correct mean360 independent sources:",
            "",
            "| Method | True mean | Missed feasible improvement | Max NLL gap |",
            "|---|---|---:|---:|",
        ]
        for mode in modes:
            for family in ["pspl", "gaussian"]:
                d = local["groups"][f"ou_biased/complete/{family}/{mode}"]
                lines.append(
                    f"| {mode} | {family} | {d['missed_feasible_improvement']}/{d['available_fits']} | {d['worst']['nll_gap']:.3f} |"
                )
        lines += [
            "",
            (
                "[Полная диагностика](covariance05/evaluation_local_minima.json), "
                "[calibration](covariance05/calibration_local_minima.json), "
                "[математическое обоснование](../research/covariance_math.md). "
                "Convergence/coverage не доказывают global optimum. Если optimization "
                "не справляется, outcome относится к конкретному finite-budget pipeline; "
                "польза ideal covariance estimation остаётся отдельным вопросом."
            ),
            "",
        ]
    lines += [
        "",
        (
            "Negative здесь означает заданную synthetic alternative к PSPL. "
            "Double bump — сумма Gaussian; реальные двухпиковые события могут "
            "требовать binary-lens и других физических моделей. Классификация "
            "всех видов микролинзирования не проверена."
        ),
        "",
    ]
    Path("reports/experiment_05.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
