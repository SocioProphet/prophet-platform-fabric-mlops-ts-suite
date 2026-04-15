from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ..interfaces import RiskModel


def _infer_step(ts: pd.Series) -> Optional[pd.Timedelta]:
    if len(ts) < 2:
        return None
    t = pd.to_datetime(ts).sort_values()
    deltas = t.diff().dropna()
    if deltas.empty:
        return None
    return deltas.median()


def _map_dist(dist: str) -> str:
    d = (dist or "").lower()
    if d in {"student_t", "students_t", "t", "student"}:
        return "StudentsT"
    if d in {"skewt", "skew_student", "skewstudent"}:
        return "SkewStudent"
    if d in {"normal", "gaussian"}:
        return "Normal"
    return "StudentsT"


@dataclass
class GARCHVolatilityModel(RiskModel):
    """Per-series conditional volatility model via `arch`.

    This is a baseline for volatility forecasting and risk systems.
    """

    variant: str = "gjr-garch"
    p: int = 1
    q: int = 1
    distribution: str = "student_t"
    mean: str = "Zero"  # Zero or Constant

    _timestamp: str = field(init=False, default="ts")
    _target: str = field(init=False, default="y")
    _group: str = field(init=False, default="sym")
    _models: Dict[str, Any] = field(init=False, default_factory=dict)

    def fit(self, df: pd.DataFrame, *, timestamp: str, target: str, group: str, **kwargs: Any) -> None:
        self._timestamp = timestamp
        self._target = target
        self._group = group

        try:
            from arch import arch_model  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("The `arch` package is required for GARCH models.") from e

        df = df[[timestamp, group, target]].dropna().copy()
        df[timestamp] = pd.to_datetime(df[timestamp])
        df = df.sort_values([group, timestamp])

        self._models = {}
        variant = (self.variant or "").lower()
        if "egarch" in variant:
            vol = "EGARCH"
            o = 0
        else:
            vol = "GARCH"
            o = 1 if ("gjr" in variant or "tgarch" in variant) else 0

        dist = _map_dist(self.distribution)

        for sym, gdf in df.groupby(group):
            y = gdf[target].astype(float).values
            if len(y) < 50:
                continue

            # The arch package expects returns (often scaled). We keep raw here; caller can scale if desired.
            am = arch_model(
                y,
                mean=self.mean,
                vol=vol,
                p=int(self.p),
                o=int(o),
                q=int(self.q),
                dist=dist,
                rescale=False,
            )
            res = am.fit(disp="off")
            self._models[str(sym)] = {
                "result": res,
                "last_ts": gdf[timestamp].iloc[-1],
                "step": _infer_step(gdf[timestamp]),
            }

    def predict_vol(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> pd.DataFrame:
        if horizon <= 0:
            raise ValueError("horizon must be > 0")

        syms = sorted({str(s) for s in df_context[self._group].unique()}) if self._group in df_context.columns else list(self._models.keys())

        rows = []
        for sym in syms:
            info = self._models.get(str(sym))
            if info is None:
                continue
            res = info["result"]
            last_ts = pd.Timestamp(info["last_ts"])
            step = info.get("step")

            if step is not None and pd.notna(step) and step != pd.Timedelta(0):
                future_ts = [last_ts + step * (i + 1) for i in range(horizon)]
            else:
                future_ts = [last_ts + pd.Timedelta(seconds=i + 1) for i in range(horizon)]

            fc = res.forecast(horizon=horizon, reindex=False)
            # fc.variance is a DataFrame-like; last row = forecasts from last observation
            var = np.asarray(fc.variance.values[-1], dtype=float)
            vol = np.sqrt(np.maximum(var, 0.0))

            for i in range(horizon):
                rows.append(
                    {
                        "ts": future_ts[i],
                        "sym": sym,
                        "variance": float(var[i]),
                        "vol": float(vol[i]),
                    }
                )

        return pd.DataFrame(rows)
