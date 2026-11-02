"""Generate the R2 numerical table and bounded interpretation from saved verified metrics."""

import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary", type=Path)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("Preserve existing report")
    result, verifier, policy = [
        json.loads(f.read_text()) for f in [args.summary, args.verifier, args.policy]
    ]
    if verifier["status"] != "PASS":
        raise SystemExit("Independent verifier must pass before publication")
    lines = [
        "# R2: новый controlled missingness эксперимент — 02.11.2026",
        "",
        (
            "Протокол зафиксирован до данных;12 development pairs использованы только для проверки кода/стоимости. "
            "Основная calibration:240 независимых пар; evaluation:360 новых пар, три seeds. "
            "В каждой паре PSPL/Gaussian согласованы по nuisance и шуму. SNR15, white heteroskedastic noise."
        ),
        "",
        (
            "Это новый ограниченный опыт; исторические результаты остаются REPORTED_ONLY. "
            "Искусственное удаление true peak — вмешательство генератора, недоступное детектору."
        ),
        "",
        "## Результаты из сохранённых решений",
        "",
        "| Условие | Точек | AUC [парный95%CI] | FP / negative; FPR [95%CI] | TP / positive; recall | Coverage |",
        "|---|---:|---|---|---|---|",
    ]
    for c in ["complete", "random40", "peak40"]:
        m = result["conditions"][c]
        a, f = m["auc_ci95_pair_bootstrap"], m["fpr_all_ci95"]
        lines.append(
            f"| {c} | {96 if c == 'complete' else 58} | {m['auc']:.4f} [{a[0]:.4f};{a[1]:.4f}] "
            f"| {m['fp']}/{m['negatives']}; {100 * m['fpr_all']:.2f}% [{100 * f[0]:.2f};{100 * f[1]:.2f}] "
            f"| {m['tp']}/{m['positives']}; {100 * m['recall_all']:.2f}% | {100 * m['coverage']:.2f}% |"
        )
    primary = result["primary_contrast"]
    ci = primary["ci95_pair_bootstrap"]
    lines += [
        "",
        (
            f"Primary AUC_peak40−AUC_random40 = **{primary['value']:.4f}**, "
            f"парный95%CI **[{ci[0]:.4f};{ci[1]:.4f}]**,500 bootstrap replicates по latent pair, стратификация по seed."
        ),
        "",
        (
            "Отрицательная разность поддерживает заранее заданный эффект в этой controlled population."
            if ci[1] < 0
            else "Предзаданный критерий отрицательной разности с CI ниже нуля не выполнен."
        ),
        "",
        (
            f"Порог **{policy['threshold']:.8f}** выбран на complete calibration negatives "
            f"({policy['calibration_fp']}/{policy['n_negative']} FP), затем применён без изменения. "
            "Целевые5% на calibration не являются гарантией на evaluation или при ином покрытии."
        ),
        "",
        "## Интерпретация и ограничения",
        "",
        (
            "AUC использует budget-limited fit score, включая best finite iterate при отсутствии converged start. "
            "Operational rule отвергает такие fits: отказы включены в знаменатель recall_all, а FPR_all считается по всем negative. "
            "Малый FPR при низком recall не означает полезного обнаружения. BIC-score не probability."
        ),
        "",
        (
            "Одинаковое число оставшихся точек позволяет отделить место пропуска от их количества в рамках этого генератора. "
            "Эффект не доказывает фундаментальную невозможность composite detection: остаются модельные priors, "
            "конечный optimizer budget и заданные negative shapes. Отдельные параметры линзы здесь не оценены по accuracy/coverage."
        ),
        "",
        (
            "Binomial CI относятся к независимым источникам одного условия и условны на замороженной policy; "
            "неопределённость calibration не маргинализирована. Все три masked views в bootstrap остаются вместе; "
            "они не утроили число независимых источников. Другие SNR/noise families, реальные телескопы, CNN и covariance-aware fitting не проверялись."
        ),
        "",
        "## Воспроизводимость",
        "",
        (
            f"Evaluation runtime: {result['runtime_seconds']:.2f}s на4 workers; maximum per-worker RSS "
            f"{result['maximum_worker_rss_kib']}KiB, не суммарная память. "
            f"Independent verifier пересчитал {verifier['fit_rows']} fit rows; "
            f"max absolute numeric difference {verifier['max_absolute_metric_difference']:.3g}."
        ),
        "",
        (
            "Протокол: [reconstruction_02_protocol.md](../research/reconstruction_02_protocol.md). "
            "Frozen policy commit: a0eb03b, до генерации evaluation. "
            "Полные scores/point metrics/CI по условиям и seed: [summary](reconstruction02/evaluation_summary.json). "
            "Raw archives и SHA256: [артефакты](reconstruction02/artifacts.json). "
            "Логи проверки: [verifier](checks/reconstruction02_evaluation_verifier.json)."
        ),
        "",
        "![Результаты R2](figures/reconstruction02_metrics.png)",
        "",
        (
            "График и таблица автоматически построены из JSON без нового fit или изменения threshold. "
            "Для повторения: распаковать raw archive; выполнить verify_reconstruction02.py с --summary и --policy, "
            "затем plot_reconstruction02.py/write_reconstruction02_report.py."
        ),
        "",
        (
            "Следующий вопрос: насколько шумовая covariance меняет надёжность и можно ли оценить её по наблюдениям "
            "без поглощения физического сигнала. Нужен отдельный protocol/namespace; это не доказанная польза GP."
        ),
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
