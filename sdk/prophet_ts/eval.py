from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .metrics import mae, rmse


@dataclass
class WalkForwardSplit:
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def make_walk_forward_splits(
    df: pd.DataFrame,
    *,
    ts_col: str,
    n_splits: int,
    train_window: int,
    test_window: int,
) -> List[WalkForwardSplit]:
    # df must be sorted by time
    ts = pd.to_datetime(df[ts_col])
    unique_ts = np.sort(ts.unique())

    splits: List[WalkForwardSplit] = []
    max_start = len(unique_ts) - (train_window + test_window)
    if max_start <= 0:
        return splits

    # evenly spaced split starts
    starts = np.linspace(0, max_start, num=n_splits, dtype=int)
    for s in starts:
        train_end = unique_ts[s + train_window - 1]
        test_start = unique_ts[s + train_window]
        test_end = unique_ts[s + train_window + test_window - 1]
        splits.append(WalkForwardSplit(pd.Timestamp(train_end), pd.Timestamp(test_start), pd.Timestamp(test_end)))

    return splits


def evaluate_point_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return {"mae": mae(y_true, y_pred), "rmse": rmse(y_true, y_pred)}
