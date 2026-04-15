from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..interfaces import ForecastModel, ForecastResult


def _infer_step(ts: pd.Series) -> Optional[pd.Timedelta]:
    if len(ts) < 2:
        return None
    t = pd.to_datetime(ts).sort_values()
    deltas = t.diff().dropna()
    if deltas.empty:
        return None
    return deltas.median()


def _make_lag_matrix(y: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y_target) for one-step ahead prediction.

    X rows correspond to time t, with features [y_{t-1}, ..., y_{t-lags}]
    y_target is y_t.
    """
    if lags <= 0:
        raise ValueError("lags must be > 0")
    n = len(y)
    if n <= lags:
        return np.empty((0, lags)), np.empty((0,))
    X = np.zeros((n - lags, lags), dtype=float)
    yt = y[lags:].astype(float)
    for i in range(lags, n):
        # lag1 = y[i-1], lag2 = y[i-2], ...
        X[i - lags, :] = y[i - 1 : i - lags - 1 : -1]
    return X, yt


@dataclass
class GBMForecaster(ForecastModel):
    """Gradient-boosted / tree-based forecaster using lag features.

    This implementation uses scikit-learn's HistGradientBoostingRegressor to keep it OSS-friendly
    and lightweight. You can swap to XGBoost/LightGBM/CatBoost behind the same interface.

    Notes:
    - Fits a separate model per group (symbol). For many symbols, consider a global model.
    - Multi-step forecast is done recursively (one-step model rolled forward).
    """

    lags: int = 64
    features: Optional[List[str]] = None
    max_depth: Optional[int] = None
    learning_rate: float = 0.05
    max_iter: int = 500
    random_state: int = 42

    _timestamp: str = field(init=False, default="ts")
    _target: str = field(init=False, default="y")
    _group: str = field(init=False, default="sym")
    _models: Dict[str, Any] = field(init=False, default_factory=dict)

    def fit(self, df: pd.DataFrame, *, timestamp: str, target: str, group: str, **kwargs: Any) -> None:
        self._timestamp = timestamp
        self._target = target
        self._group = group

        try:
            from sklearn.ensemble import HistGradientBoostingRegressor  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("scikit-learn is required for GBMForecaster.") from e

        df = df[[timestamp, group, target]].dropna().copy()
        df[timestamp] = pd.to_datetime(df[timestamp])
        df = df.sort_values([group, timestamp])

        self._models = {}
        for sym, gdf in df.groupby(group):
            y = gdf[target].astype(float).values
            X, yt = _make_lag_matrix(y, self.lags)
            if X.shape[0] < 200:
                continue

            m = HistGradientBoostingRegressor(
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                max_iter=self.max_iter,
                random_state=self.random_state,
            )
            m.fit(X, yt)

            self._models[str(sym)] = {
                "model": m,
                "last_ts": gdf[timestamp].iloc[-1],
                "step": _infer_step(gdf[timestamp]),
                "last_values": y[-self.lags :].tolist(),
            }

    def predict(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> ForecastResult:
        if horizon <= 0:
            raise ValueError("horizon must be > 0")

        syms = sorted({str(s) for s in df_context[self._group].unique()}) if self._group in df_context.columns else list(self._models.keys())

        rows = []
        for sym in syms:
            info = self._models.get(str(sym))
            if info is None:
                continue
            m = info["model"]
            last_ts = pd.Timestamp(info["last_ts"])
            step = info.get("step")
            history = list(info["last_values"])

            if step is not None and pd.notna(step) and step != pd.Timedelta(0):
                future_ts = [last_ts + step * (i + 1) for i in range(horizon)]
            else:
                future_ts = [last_ts + pd.Timedelta(seconds=i + 1) for i in range(horizon)]

            for i in range(horizon):
                x = np.array(history[-self.lags :][::-1], dtype=float).reshape(1, -1)
                yhat = float(m.predict(x)[0])
                history.append(yhat)
                rows.append({"ts": future_ts[i], "sym": sym, "yhat": yhat})

        mean_df = pd.DataFrame(rows)
        return ForecastResult(mean=mean_df, quantiles=None, params={"family": "gbm", "lags": self.lags})
