"""Multinomial logistic regression (softmax) with L2 penalty, fitted by
Newton's method. Small, dependency-free reference model for the empirical
prediction tests. The first class is the reference category."""

from __future__ import annotations

import numpy as np


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class MultinomialLogit:
    def __init__(self, l2: float = 1.0, max_iter: int = 100, tol: float = 1e-8):
        self.l2 = float(l2)
        self.max_iter = max_iter
        self.tol = tol
        self.coef_: np.ndarray | None = None  # (n_features + 1, n_classes - 1)

    @staticmethod
    def _design(X: np.ndarray) -> np.ndarray:
        return np.hstack([np.ones((X.shape[0], 1)), np.asarray(X, dtype=float)])

    def fit(self, X: np.ndarray, y: np.ndarray, n_classes: int, sample_weight: np.ndarray | None = None):
        A = self._design(X)
        n, p = A.shape
        k = n_classes - 1
        w = np.ones(n) if sample_weight is None else np.asarray(sample_weight, dtype=float)
        Y = np.zeros((n, n_classes))
        Y[np.arange(n), y] = 1.0
        beta = np.zeros((p, k))
        pen = np.full(p, self.l2)
        pen[0] = 0.0  # intercept not penalised
        for _ in range(self.max_iter):
            P = self.predict_proba_design(A, beta)
            R = (Y - P)[:, 1:] * w[:, None]
            grad = (A.T @ R - pen[:, None] * beta).reshape(-1, order="F")
            H = np.zeros((p * k, p * k))
            Pk = P[:, 1:]
            for a in range(k):
                for b in range(k):
                    d = (Pk[:, a] * ((a == b) - Pk[:, b])) * w
                    H[a * p:(a + 1) * p, b * p:(b + 1) * p] = -(A.T * d) @ A
            H -= np.diag(np.tile(pen, k))
            step = np.linalg.solve(H, grad)
            beta = beta - step.reshape((p, k), order="F")
            if np.max(np.abs(step)) < self.tol:
                break
        self.coef_ = beta
        self.n_classes = n_classes
        return self

    @staticmethod
    def predict_proba_design(A: np.ndarray, beta: np.ndarray) -> np.ndarray:
        z = np.hstack([np.zeros((A.shape[0], 1)), A @ beta])
        return softmax(z)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba_design(self._design(X), self.coef_)


def log_loss(P: np.ndarray, y: np.ndarray, eps: float = 1e-6) -> float:
    p = np.clip(P[np.arange(len(y)), y], eps, 1.0)
    return float(-np.mean(np.log(p)))


def brier(P: np.ndarray, y: np.ndarray) -> float:
    Y = np.zeros_like(P)
    Y[np.arange(len(y)), y] = 1.0
    return float(np.mean(np.sum((P - Y) ** 2, axis=1)))


def auc(score: np.ndarray, positive: np.ndarray) -> float:
    """Area under the ROC curve via the rank statistic (ties averaged)."""
    score = np.asarray(score, dtype=float)
    pos = np.asarray(positive, dtype=bool)
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score))
    s = score[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
