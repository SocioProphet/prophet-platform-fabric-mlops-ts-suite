# ProphetModelSpec (declarative model definition)

Prophet treats models as **declarative specs** rather than “ad hoc notebooks”.
This is how we make training/serving reproducible and portable across engines (RayJob, K8s Job, Spark).

## Where to look
- Examples: `model-specs/*.yaml`
- JSON Schema: `schemas/prophet-model-spec.schema.json`

## Key design choices
- **Task-first:** spec.task defines what the model *does* (forecast, risk, surface, etc.).
- **Dataset versioned:** spec.dataset.uri points at a manifest or parquet path that is immutable/versioned.
- **Model family + params:** spec.model.family chooses an engine adapter; additional keys become params.
- **Engine is a choice:** spec.train.engine and spec.serve.engine specify how to execute/deploy; Prophet contracts stay stable.
- **Gates are explicit:** spec.eval.gates defines promotion conditions.

## Minimal example

```yaml
kind: ProphetModelSpec
metadata:
  name: arima-forecast-v1
spec:
  task: forecast.multi_horizon
  dataset:
    uri: s3://lake/manifests/bars_5m/v2026-01-14T12:00Z.json
    target: return_5m
    timestamp: ts
    group: sym
  model:
    family: arima
    order: [1,0,0]
  train:
    engine: k8sjob
    image: ghcr.io/prophet-platform/prophet-models-classical:0.2.0
  serve:
    mode: nearline
    schedule: "*/5 * * * *"
  eval:
    gates:
      - metric: rmse
        op: "<="
        value: 0.012
```

The training image reads this spec and produces:
- `metrics.json`
- a model artifact (`model.pkl`, `checkpoint.pt`, etc.)
- optional forecast tables (parquet)

Then the Argo workflow runs `prophet_ts.gating` to decide promotion.

