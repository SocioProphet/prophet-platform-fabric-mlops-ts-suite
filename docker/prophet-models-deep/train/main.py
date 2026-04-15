import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from prophet_ts.io import load_dataset_from_uri
from prophet_ts.model_factory import build_model
from prophet_ts.spec import load_model_spec
from prophet_ts.eval import evaluate_point_forecast


def _split_train_test(df: pd.DataFrame, *, ts: str, group: str, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df[ts] = pd.to_datetime(df[ts])
    df = df.sort_values([group, ts])
    train_parts = []
    test_parts = []
    for _, gdf in df.groupby(group):
        if len(gdf) <= horizon + 200:
            continue
        train_parts.append(gdf.iloc[:-horizon])
        test_parts.append(gdf.iloc[-horizon:])
    if not train_parts:
        raise ValueError("Not enough data to create train/test split.")
    return pd.concat(train_parts, ignore_index=True), pd.concat(test_parts, ignore_index=True)


def _eval_forecast(test_df: pd.DataFrame, pred_df: pd.DataFrame, *, ts: str, group: str, target: str) -> Dict[str, float]:
    if pred_df.empty:
        return {"mae": float("nan"), "rmse": float("nan")}
    test_df = test_df.copy()
    pred_df = pred_df.copy()
    test_df[ts] = pd.to_datetime(test_df[ts])
    pred_df[ts] = pd.to_datetime(pred_df[ts])

    merged = test_df[[ts, group, target]].merge(pred_df[[ts, group, "yhat"]], on=[ts, group], how="inner")
    if len(merged) >= 10:
        y_true = merged[target].astype(float).values
        y_pred = merged["yhat"].astype(float).values
        return evaluate_point_forecast(y_true, y_pred)

    ys_true = []
    ys_pred = []
    for sym, gtest in test_df.sort_values([group, ts]).groupby(group):
        gpred = pred_df[pred_df[group] == str(sym)].sort_values(ts)
        m = min(len(gtest), len(gpred))
        if m == 0:
            continue
        ys_true.append(gtest[target].astype(float).values[:m])
        ys_pred.append(gpred["yhat"].astype(float).values[:m])
    if not ys_true:
        return {"mae": float("nan"), "rmse": float("nan")}
    y_true = np.concatenate(ys_true)
    y_pred = np.concatenate(ys_pred)
    return evaluate_point_forecast(y_true, y_pred)


def _maybe_log_mlflow(spec: Any, metrics: Dict[str, Any], artifacts_dir: Path) -> None:
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        return
    try:
        import mlflow  # type: ignore
    except Exception:
        return

    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    exp = os.environ.get("MLFLOW_EXPERIMENT_NAME", "prophet-ts")
    mlflow.set_experiment(exp)

    with mlflow.start_run(run_name=spec.name or None):
        mlflow.log_param("task", spec.task)
        mlflow.log_param("family", spec.model.family)
        for k, v in (spec.model.params or {}).items():
            if isinstance(v, (str, int, float, bool)):
                mlflow.log_param(k, v)
        for k, v in metrics.items():
            if isinstance(v, (int, float)) and np.isfinite(v):
                mlflow.log_metric(k, float(v))
        for p in artifacts_dir.glob("*"):
            if p.is_file():
                mlflow.log_artifact(str(p))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--horizon", type=int, default=0)
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    spec = load_model_spec(args.spec)
    df = load_dataset_from_uri(spec.dataset.uri)

    ts = spec.dataset.timestamp
    group = spec.dataset.group
    target = spec.dataset.target

    horizon = int(args.horizon or spec.model.params.get("horizon", 0) or spec.model.params.get("h", 0) or 24)
    train_df, test_df = _split_train_test(df, ts=ts, group=group, horizon=horizon)

    model = build_model(spec.model.family, **(spec.model.params or {}))
    model.fit(train_df, timestamp=ts, target=target, group=group)

    pred = model.predict(train_df, horizon=horizon).mean
    metrics = {
        "status": "ok",
        "task": spec.task,
        "model_family": spec.model.family,
        "horizon": horizon,
    }
    metrics.update(_eval_forecast(test_df, pred, ts=ts, group=group, target=target))

    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # Save a checkpoint if torch is available and model exposes it.
    try:
        import torch  # type: ignore
        if hasattr(model, "_model") and model._model is not None:
            torch.save(model._model.state_dict(), out / "checkpoint.pt")
    except Exception:
        pass

    pred.to_parquet(out / "forecast.parquet", index=False)

    _maybe_log_mlflow(spec, metrics, out)
    print("Wrote artifacts to", out)


if __name__ == "__main__":
    main()
