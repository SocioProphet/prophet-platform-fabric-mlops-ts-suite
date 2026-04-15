from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..interfaces import ForecastModel, ForecastResult


def _build_windows(
    df: pd.DataFrame,
    *,
    ts_col: str,
    y_col: str,
    group_col: str,
    context_window: int,
    horizon: int,
    max_per_series: Optional[int] = None,
) -> tuple[np.ndarray, np.ndarray]:
    Xs: List[np.ndarray] = []
    Ys: List[np.ndarray] = []

    df = df[[ts_col, group_col, y_col]].dropna().copy()
    df[ts_col] = pd.to_datetime(df[ts_col])

    for _, gdf in df.sort_values([group_col, ts_col]).groupby(group_col):
        y = gdf[y_col].astype(float).values
        if len(y) < context_window + horizon + 1:
            continue
        count = 0
        for start in range(0, len(y) - (context_window + horizon) + 1):
            x = y[start : start + context_window]
            yy = y[start + context_window : start + context_window + horizon]
            Xs.append(x.reshape(context_window, 1))
            Ys.append(yy)
            count += 1
            if max_per_series is not None and count >= max_per_series:
                break

    if not Xs:
        return np.empty((0, context_window, 1)), np.empty((0, horizon))
    return np.stack(Xs, axis=0), np.stack(Ys, axis=0)


@dataclass
class TransformerForecaster(ForecastModel):
    """Minimal transformer encoder forecaster baseline.

    This is a *reference implementation* to keep Prophet’s contracts honest.
    Swap in better architectures as you iterate (patching, decomposition, etc.).
    """

    context_window: int = 2048
    horizon: int = 24
    d_model: int = 128
    nhead: int = 4
    num_layers: int = 4
    dim_feedforward: int = 256
    dropout: float = 0.1

    epochs: int = 5
    batch_size: int = 128
    lr: float = 1e-3
    max_windows_per_series: int = 200

    device: str = "cpu"

    _timestamp: str = field(init=False, default="ts")
    _target: str = field(init=False, default="y")
    _group: str = field(init=False, default="sym")
    _model: Any = field(init=False, default=None)
    _trained: bool = field(init=False, default=False)

    def fit(self, df: pd.DataFrame, *, timestamp: str, target: str, group: str, **kwargs: Any) -> None:
        self._timestamp = timestamp
        self._target = target
        self._group = group

        try:
            import torch  # type: ignore
            import torch.nn as nn  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("PyTorch is required for TransformerForecaster.") from e

        X, Y = _build_windows(
            df,
            ts_col=timestamp,
            y_col=target,
            group_col=group,
            context_window=self.context_window,
            horizon=self.horizon,
            max_per_series=self.max_windows_per_series,
        )
        if X.shape[0] == 0:
            raise ValueError("Not enough data to build training windows.")

        x = torch.tensor(X, dtype=torch.float32)  # (N, T, 1)
        y = torch.tensor(Y, dtype=torch.float32)  # (N, H)

        class Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.in_proj = nn.Linear(1, self.d_model)
                enc_layer = nn.TransformerEncoderLayer(
                    d_model=self.d_model,
                    nhead=self.nhead,
                    dim_feedforward=self.dim_feedforward,
                    dropout=self.dropout,
                    batch_first=True,
                )
                self.encoder = nn.TransformerEncoder(enc_layer, num_layers=self.num_layers)
                self.head = nn.Linear(self.d_model, self.horizon)

            def forward(self, x):
                # x: (B, T, 1)
                h = self.in_proj(x)
                z = self.encoder(h)
                # take last token representation
                last = z[:, -1, :]
                out = self.head(last)  # (B, H)
                return out

        self._model = Model().to(self.device)
        opt = torch.optim.Adam(self._model.parameters(), lr=self.lr)

        self._model.train()
        n = x.shape[0]
        idx = torch.randperm(n)
        x = x[idx]
        y = y[idx]

        for ep in range(self.epochs):
            for i in range(0, n, self.batch_size):
                xb = x[i : i + self.batch_size].to(self.device)
                yb = y[i : i + self.batch_size].to(self.device)
                opt.zero_grad()
                pred = self._model(xb)
                loss = torch.mean((pred - yb) ** 2)
                loss.backward()
                opt.step()

        self._trained = True

    def predict(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> ForecastResult:
        if not self._trained:
            raise RuntimeError("Model is not trained.")
        if horizon != self.horizon:
            raise ValueError(f"horizon mismatch: model horizon={self.horizon}, requested={horizon}")

        import torch  # type: ignore

        df = df_context[[self._timestamp, self._group, self._target]].dropna().copy()
        df[self._timestamp] = pd.to_datetime(df[self._timestamp])

        rows = []
        self._model.eval()
        with torch.no_grad():
            for sym, gdf in df.sort_values([self._group, self._timestamp]).groupby(self._group):
                y = gdf[self._target].astype(float).values
                if len(y) < self.context_window:
                    continue
                ctx = y[-self.context_window :].reshape(1, self.context_window, 1)
                x = torch.tensor(ctx, dtype=torch.float32).to(self.device)
                pred = self._model(x).cpu().numpy()[0]  # (H,)

                last_ts = gdf[self._timestamp].iloc[-1]
                step = (gdf[self._timestamp].diff().dropna().median() if len(gdf) > 2 else pd.Timedelta(seconds=1))
                future_ts = [pd.Timestamp(last_ts) + step * (i + 1) for i in range(self.horizon)]

                for i in range(self.horizon):
                    rows.append({"ts": future_ts[i], "sym": str(sym), "yhat": float(pred[i])})

        mean_df = pd.DataFrame(rows)
        return ForecastResult(mean=mean_df, quantiles=None, params={"family": "deep.transformer"})
