import argparse
import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from prophet_ts.io import load_dataset_from_uri
from prophet_ts.model_factory import build_model
from prophet_ts.spec import load_model_spec


def _split_train_test(df: pd.DataFrame, *, ts: str, group: str, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df[ts] = pd.to_datetime(df[ts])
    df = df.sort_values([group, ts])
    train_parts = []
    test_parts = []
    for _, gdf in df.groupby(group):
        if len(gdf) <= horizon + 50:
            continue
        train_parts.append(gdf.iloc[:-horizon])
        test_parts.append(gdf.iloc[-horizon:])
    if not train_parts:
        raise ValueError("Not enough data to create train/test split.")
    return pd.concat(train_parts, ignore_index=True), pd.concat(test_parts, ignore_index=True)


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

    horizon = int(args.horizon or spec.model.params.get("horizon", 0) or 10)
    train_df, test_df = _split_train_test(df, ts=ts, group=group, horizon=horizon)

    model = build_model(spec.model.family, **(spec.model.params or {}))
    model.fit(train_df, timestamp=ts, target=target, group=group)

    vol_df = model.predict_vol(train_df, horizon=horizon)
    metrics = {
        "status": "ok",
        "task": spec.task,
        "model_family": spec.model.family,
        "horizon": horizon,
    }

    # Naive evaluation: compare forecasted variance to realized squared returns on test window (order-aligned).
    # This is a placeholder; replace with QLIKE / proper realized-vol targets.
    test_df = test_df.sort_values([group, ts])
    vol_df = vol_df.sort_values([group, "ts"])
    ys_true = []
    ys_pred = []
    for sym, gtest in test_df.groupby(group):
        gvol = vol_df[vol_df[group] == str(sym)]
        m = min(len(gtest), len(gvol))
        if m == 0:
            continue
        r = gtest[target].astype(float).values[:m]
        ys_true.append((r ** 2))
        ys_pred.append(gvol["variance"].astype(float).values[:m])
    if ys_true:
        y_true = np.concatenate(ys_true)
        y_pred = np.concatenate(ys_pred)
        metrics["mse_variance"] = float(np.mean((y_true - y_pred) ** 2))
    else:
        metrics["mse_variance"] = float("nan")

    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    try:
        with open(out / "model.pkl", "wb") as f:
            pickle.dump(model, f)
    except Exception as e:
        (out / "model.txt").write_text(f"Pickle failed: {e}\n")

    # Write forecast table
    vol_df.to_parquet(out / "vol_forecast.parquet", index=False)

    _maybe_log_mlflow(spec, metrics, out)
    print("Wrote artifacts to", out)


if __name__ == "__main__":
    main()
