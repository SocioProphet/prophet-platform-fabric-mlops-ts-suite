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
    """Build supervised windows for sequence-to-sequence style forecasting.

    Returns:
      X: (N, context_window, 1)
      Y: (N, horizon)
    """
    Xs: List[np.ndarray] = []
    Ys: List[np.ndarray] = []

    df = df[[ts_col, group_col, y_col]].dropna().copy()
    df[ts_col] = pd.to_datetime(df[ts_col])

    for _, gdf in df.sort_values([group_col, ts_col]).groupby(group_col):
        y = gdf[y_col].astype(float).values
        if len(y) < context_window + horizon + 1:
            continue
        # Sliding windows
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


def _pinball(y: "torch.Tensor", yq: "torch.Tensor", q: float) -> "torch.Tensor":  # type: ignore
    diff = y - yq
    return (torch.maximum(q * diff, (q - 1.0) * diff)).mean()


@dataclass
class Seq2SeqForecaster(ForecastModel):
    """Minimal GRU-based multi-horizon forecaster.

    This is not meant to be the final word in deep forecasting; it is a *reference baseline*
    that fits Prophet’s standard interfaces.
    """

    context_window: int = 512
    horizon: int = 60
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.1

    loss: str = "pinball"  # pinball | mse
    quantiles: List[float] = field(default_factory=lambda: [0.1, 0.5, 0.9])

    epochs: int = 5
    batch_size: int = 256
    lr: float = 1e-3
    max_windows_per_series: int = 500

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
            raise RuntimeError("PyTorch is required for Seq2SeqForecaster.") from e

        # Build windows
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

        x = torch.tensor(X, dtype=torch.float32)
        y = torch.tensor(Y, dtype=torch.float32)

        # Model: GRU encoder -> linear horizon head (optionally multi-quantile)
        n_out = len(self.quantiles) if self.loss == "pinball" else 1

        class Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.gru = nn.GRU(
                    input_size=1,
                    hidden_size=self.hidden_size,
                    num_layers=self.num_layers,
                    batch_first=True,
                    dropout=self.dropout if self.num_layers > 1 else 0.0,
                )
                self.head = nn.Linear(self.hidden_size, self.horizon * n_out)

            def forward(self, x):
                _, h = self.gru(x)  # h: (layers, batch, hidden)
                h_last = h[-1]      # (batch, hidden)
                out = self.head(h_last).view(-1, self.horizon, n_out)
                return out

        self._model = Model().to(self.device)
        opt = torch.optim.Adam(self._model.parameters(), lr=self.lr)

        def loss_fn(pred: "torch.Tensor", y_true: "torch.Tensor") -> "torch.Tensor":  # type: ignore
            if self.loss == "mse":
                # pred: (B, H, 1)
                return torch.mean((pred.squeeze(-1) - y_true) ** 2)
            # pinball across quantiles
            total = 0.0
            for qi, q in enumerate(self.quantiles):
                total = total + _pinball(y_true, pred[:, :, qi], float(q))
            return total / len(self.quantiles)

        # Simple SGD loop
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
                loss = loss_fn(pred, yb)
                loss.backward()
                opt.step()

        self._trained = True

    def predict(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> ForecastResult:
        if not self._trained:
            raise RuntimeError("Model is not trained.")
        if horizon != self.horizon:
            # keep it strict for now (simplifies)
            raise ValueError(f"horizon mismatch: model horizon={self.horizon}, requested={horizon}")

        import torch  # type: ignore

        df = df_context[[self._timestamp, self._group, self._target]].dropna().copy()
        df[self._timestamp] = pd.to_datetime(df[self._timestamp])

        mean_rows = []
        q_rows = []

        self._model.eval()
        with torch.no_grad():
            for sym, gdf in df.sort_values([self._group, self._timestamp]).groupby(self._group):
                y = gdf[self._target].astype(float).values
                if len(y) < self.context_window:
                    continue
                ctx = y[-self.context_window :].reshape(1, self.context_window, 1)
                x = torch.tensor(ctx, dtype=torch.float32).to(self.device)
                pred = self._model(x).cpu().numpy()[0]  # (H, n_out)

                # Build future timestamps (best-effort)
                last_ts = gdf[self._timestamp].iloc[-1]
                step = (gdf[self._timestamp].diff().dropna().median() if len(gdf) > 2 else pd.Timedelta(seconds=1))
                future_ts = [pd.Timestamp(last_ts) + step * (i + 1) for i in range(self.horizon)]

                if self.loss == "pinball":
                    # choose q0.5 as mean-ish output
                    try:
                        q_idx = self.quantiles.index(0.5)
                    except ValueError:
                        q_idx = 0
                    yhat = pred[:, q_idx]
                    for i in range(self.horizon):
                        mean_rows.append({"ts": future_ts[i], "sym": str(sym), "yhat": float(yhat[i])})
                        qrec = {"ts": future_ts[i], "sym": str(sym)}
                        for qi, q in enumerate(self.quantiles):
                            qrec[f"q{float(q)}"] = float(pred[i, qi])
                        q_rows.append(qrec)
                else:
                    yhat = pred[:, 0]
                    for i in range(self.horizon):
                        mean_rows.append({"ts": future_ts[i], "sym": str(sym), "yhat": float(yhat[i])})

        mean_df = pd.DataFrame(mean_rows)
        quant_df = pd.DataFrame(q_rows) if q_rows else None
        return ForecastResult(mean=mean_df, quantiles=quant_df, params={"family": "deep.seq2seq"})
