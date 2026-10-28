"""Scores a hallucination detector's predictions against the labeled
benchmark examples from src/benchmark/datasets.py, and reports metrics
that let the NLI-based checker and the embedding-similarity baseline be
compared head-to-head.

Treated as binary classification (hallucinated vs. supported) at the
whole-answer level: an answer counts as "predicted hallucinated" if
run_benchmark.py finds at least one unsupported claim in it. That's the
granularity HaluEval's labels are at (one label per answer, not per
claim), so it's what these metrics score against -- even though the
checkers themselves operate per-claim internally.
"""

from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def compute_classification_metrics(y_true: list[bool], y_pred: list[bool]) -> dict:
    """Computes precision/recall/F1/accuracy for hallucination predictions.

    Args:
        y_true: ground-truth hallucination labels (True = hallucinated).
        y_pred: predicted hallucination labels from a checker.

    Returns:
        A dict with keys "accuracy", "precision", "recall", "f1".
        Precision/recall/F1 treat "hallucinated" (True) as the positive
        class, since that's the case we actually care about catching.
    """
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=True, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def compute_expected_calibration_error(y_true: list[bool], y_probs: list[float], n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) across confidence bins."""
    import numpy as np

    if not y_true or not y_probs or len(y_true) != len(y_probs):
        return 0.0

    y_t = np.array(y_true, dtype=bool)
    y_p = np.array(y_probs, dtype=float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_n = len(y_t)

    for i in range(n_bins):
        b_low, b_high = bins[i], bins[i + 1]
        in_bin = (y_p >= b_low) & (y_p <= b_high) if i == 0 else (y_p > b_low) & (y_p <= b_high)
        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = np.mean(y_t[in_bin])
            bin_conf = np.mean(y_p[in_bin])
            ece += (bin_size / total_n) * abs(bin_acc - bin_conf)

    return float(ece)


def compute_extended_metrics(
    y_true: list[bool],
    y_pred: list[bool],
    y_probs: list[float] | None = None,
) -> dict:
    """Computes full research evaluation metrics:

    - Accuracy, Macro F1, Binary F1
    - Per-class precision, recall, and F1 (Supported [class 0] vs Hallucinated [class 1])
    - Confusion Matrix (TP, FP, TN, FN)
    - False Positive Rate (FPR) and False Negative Rate (FNR)
    - Brier score & Expected Calibration Error (ECE) if probabilities are provided
    """
    import numpy as np
    from sklearn.metrics import confusion_matrix, brier_score_loss

    base = compute_classification_metrics(y_true, y_pred)

    # Per-class scores
    p_per_class, r_per_class, f1_per_class, _ = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=[False, True], zero_division=0
    )
    macro_f1 = float(np.mean(f1_per_class))

    # Confusion matrix
    # labels=[False, True] -> [[tn, fp], [fn, tp]]
    cm = confusion_matrix(y_true, y_pred, labels=[False, True])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    result = {
        **base,
        "macro_f1": macro_f1,
        "supported_f1": float(f1_per_class[0]),
        "hallucinated_f1": float(f1_per_class[1]),
        "supported_precision": float(p_per_class[0]),
        "supported_recall": float(r_per_class[0]),
        "hallucinated_precision": float(p_per_class[1]),
        "hallucinated_recall": float(r_per_class[1]),
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "fpr": fpr,
        "fnr": fnr,
        "specificity": specificity,
        "total_examples": len(y_true),
    }

    if y_probs is not None and len(y_probs) == len(y_true):
        try:
            brier = float(brier_score_loss(y_true, y_probs))
            ece = compute_expected_calibration_error(y_true, y_probs)
            result["brier_score"] = brier
            result["ece"] = ece
        except Exception:
            pass

    return result

