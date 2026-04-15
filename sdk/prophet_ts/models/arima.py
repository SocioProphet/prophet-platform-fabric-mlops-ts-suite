from __future__ import annotations

from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd

from ..interfaces import ForecastModel, ForecastResult


def _infer_step(ts: pd.Series) -> Optional[pd.Timedelta]:
    """Infer a reasonable time delta between observations."""
    if len(ts) < 2:
        return None
    t = pd.to_datetime(ts).sort_values()
    deltas = t.diff().dropna()
    if deltas.empty:
        return None
    # Use median delta (robust-ish).
    return deltas.median()


@dataclass
class ARIMAForecaster(ForecastModel):
    """Per-series ARIMA/SARIMAX forecaster (baseline/interpretable).

    Notes:
    - Fits a separate model per group (symbol).
    - Intended for baselines and interpretability, not as the sole production engine.
    """

    order: Tuple[int, int, int] = (1, 0, 0)
    seasonal_order: Optional[Tuple[int, int, int, int]] = None
    trend: Optional[str] = None
    enforce_stationarity: bool = True
    enforce_invertibility: bool = True

    _timestamp: str = field(init=False, default="ts")
    _target: str = field(init=False, default="y")
    _group: str = field(init=False, default="sym")
    _models: Dict[str, Any] = field(init=False, default_factory=dict)

    def fit(self, df: pd.DataFrame, *, timestamp: str, target: str, group: str, **kwargs: Any) -> None:
        self._timestamp = timestamp
        self._target = target
        self._group = group

        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("statsmodels is required for ARIMA/SARIMAX models.") from e

        df = df[[timestamp, group, target]].dropna().copy()
        df[timestamp] = pd.to_datetime(df[timestamp])
        df = df.sort_values([group, timestamp])

        self._models = {}
        for sym, gdf in df.groupby(group):
            y = gdf[target].astype(float).values
            if len(y) < max(20, sum(self.order) + 5):
                # too little data; skip
                continue

            mod = SARIMAX(
                y,
                order=self.order,
                seasonal_order=self.seasonal_order if self.seasonal_order is not None else (0, 0, 0, 0),
                trend=self.trend,
                enforce_stationarity=self.enforce_stationarity,
                enforce_invertibility=self.enforce_invertibility,
            )
            res = mod.fit(disp=False)
            self._models[str(sym)] = {
                "result": res,
                "last_ts": gdf[timestamp].iloc[-1],
                "step": _infer_step(gdf[timestamp]),
            }

    def predict(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> ForecastResult:
        if horizon <= 0:
            raise ValueError("horizon must be > 0")

        syms = sorted({str(s) for s in df_context[self._group].unique()}) if self._group in df_context.columns else list(self._models.keys())

        mean_rows = []
        q_rows = []
        nd = NormalDist()

        for sym in syms:
            info = self._models.get(str(sym))
            if info is None:
                continue
            res = info["result"]
            last_ts = pd.Timestamp(info["last_ts"])
            step = info.get("step")

            # Create future timestamps
            if step is not None and pd.notna(step) and step != pd.Timedelta(0):
                future_ts = [last_ts + step * (i + 1) for i in range(horizon)]
            else:
                # fallback: integer steps as strings
                future_ts = [last_ts + pd.Timedelta(seconds=i + 1) for i in range(horizon)]

            fc = res.get_forecast(steps=horizon)
            mu = fc.predicted_mean  # ndarray
            # Statsmodels provides se_mean; if missing, assume 0
            try:
                se = fc.se_mean  # type: ignore
            except Exception:
                se = [0.0] * horizon

            # Default quantiles: 0.1/0.5/0.9
            qs = kwargs.get("quantiles", [0.1, 0.5, 0.9])
            # Precompute z-scores for each quantile
            z = {float(q): nd.inv_cdf(float(q)) for q in qs}

            for i in range(horizon):
                ts_i = future_ts[i]
                yhat = float(mu[i])
                mean_rows.append({"ts": ts_i, "sym": sym, "yhat": yhat})

                qrec = {"ts": ts_i, "sym": sym}
                for q in qs:
                    qf = float(q)
                    if qf == 0.5:
                        qrec["q0.5"] = yhat
                    else:
                        qrec[f"q{qf}"] = float(yhat + float(z[qf]) * float(se[i]))
                q_rows.append(qrec)

        mean_df = pd.DataFrame(mean_rows)
        quant_df = pd.DataFrame(q_rows) if q_rows else None

        return ForecastResult(mean=mean_df, quantiles=quant_df, params={"family": "arima", "order": self.order})
