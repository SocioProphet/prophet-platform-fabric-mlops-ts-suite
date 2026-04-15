from __future__ import annotations

import numpy as np
import pandas as pd


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def pinball_loss(y_true: np.ndarray, y_q: np.ndarray, q: float) -> float:
    # y_q is the q-quantile prediction
    diff = y_true - y_q
    return float(np.mean(np.maximum(q * diff, (q - 1.0) * diff)))


def quantile_coverage(y_true: np.ndarray, y_lo: np.ndarray, y_hi: np.ndarray) -> float:
    inside = (y_true >= y_lo) & (y_true <= y_hi)
    return float(np.mean(inside))


def mase(y_true: np.ndarray, y_pred: np.ndarray, y_insample: np.ndarray, m: int = 1) -> float:
    # Mean Absolute Scaled Error
    denom = np.mean(np.abs(y_insample[m:] - y_insample[:-m]))
    if denom == 0:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / denom)


def make_eval_frame(y_true: pd.DataFrame, y_pred: pd.DataFrame, *, ts_col: str = "ts", id_col: str = "sym") -> pd.DataFrame:
    # expects columns: ts,sym,y_true and ts,sym,yhat
    df = y_true.merge(y_pred, on=[ts_col, id_col], how="inner")
    return df
