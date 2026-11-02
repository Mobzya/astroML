"""Source-level metrics for frozen decisions; a score is not a probability."""

import numpy as np
from scipy.stats import beta, rankdata


def auc_from_pairs(positive, negative):
    p, n = np.asarray(positive, float), np.asarray(negative, float)
    if p.ndim != 1 or n.ndim != 1 or not p.size or not n.size:
        raise ValueError("nonempty 1D class scores required")
    if np.any(np.isnan(p)) or np.any(np.isnan(n)):
        raise ValueError("NaN is not a score; encode failures at -infinity explicitly")
    ranks = rankdata(np.r_[p, n], method="average")
    return float((ranks[: len(p)].sum() - len(p) * (len(p) + 1) / 2) / (len(p) * len(n)))


def binomial_interval(successes, total, alpha=0.05):
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("valid independent counts required")
    lo = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, total - successes + 1))
    hi = (
        1.0
        if successes == total
        else float(beta.ppf(1 - alpha / 2, successes + 1, total - successes))
    )
    return [lo, hi]


def calibration_threshold(scores, alpha=0.05):
    values = np.sort(np.asarray(scores, float))
    if not len(values) or np.any(np.isnan(values)) or not 0 < alpha < 1:
        raise ValueError("valid calibration scores and target required")
    index = int(np.ceil((1 - alpha) * len(values))) - 1
    selected = values[index]
    return float(np.nextafter(selected, np.inf)) if np.isfinite(selected) else None


def decision_metrics(positive_scores, negative_scores, positive_valid, negative_valid, threshold):
    p, n = np.asarray(positive_scores), np.asarray(negative_scores)
    pv, nv = np.asarray(positive_valid, bool), np.asarray(negative_valid, bool)
    if not (len(p) == len(pv) == len(n) == len(nv)) or len(p) == 0:
        raise ValueError("source-paired nonempty inputs required")
    pd = pv & (p >= threshold) if threshold is not None else np.zeros(len(p), bool)
    nd = nv & (n >= threshold) if threshold is not None else np.zeros(len(n), bool)
    tp, fp, accepted = int(pd.sum()), int(nd.sum()), int(pv.sum() + nv.sum())
    fn_accepted = int((pv & ~pd).sum())
    return {
        "pairs": len(p),
        "auc": auc_from_pairs(p, n),
        "tp": tp,
        "fp": fp,
        "positives": len(p),
        "negatives": len(n),
        "fpr_all": fp / len(n),
        "fpr_all_ci95": binomial_interval(fp, len(n)),
        "recall_all": tp / len(p),
        "recall_all_ci95": binomial_interval(tp, len(p)),
        "coverage": accepted / (len(p) + len(n)),
        "rejected_positive": int((~pv).sum()),
        "rejected_negative": int((~nv).sum()),
        "fpr_accepted_negative": fp / int(nv.sum()) if nv.any() else None,
        "selective_risk": (fp + fn_accepted) / accepted if accepted else None,
        "fdr_balanced": fp / (tp + fp) if tp + fp else None,
    }
