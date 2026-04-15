# Time-series evaluation & gates (finance-grade)

This is how Prophet decides whether a model run can be promoted.

## 1) Walk-forward validation (mandatory)
- Rolling or expanding window splits
- Evaluate across multiple windows to reduce regime luck

## 2) Accuracy metrics (task-dependent)

### Mean/point forecasts
- MAE, RMSE
- MASE (robust across series)

### Quantile/probabilistic forecasts
- pinball loss
- quantile coverage
- PIT (probability integral transform) checks when full distributions exist

### Volatility forecasts
- QLIKE (common for volatility)
- MSE on realized volatility proxy

### Surfaces (IV/curves)
- RMSE on IV
- constraint violations count (no-arb checks)

## 3) Finance reality checks (recommended)
These are *not* model metrics; they are downstream sanity checks.

- turnover and transaction cost sensitivity (for trading signals)
- drawdown behavior in backtests
- stability under regime slices (e.g., high vol vs low vol)

## 4) Promotion gates (example)
- must beat baseline by X% on primary metric
- must pass calibration threshold (coverage >= 0.85)
- must not violate constraint checks

A minimal gate can be expressed in `ProphetModelSpec.eval.gates`.
See `model-specs/` examples.

## 5) Reproducibility gates (non-negotiable)
Promotion is refused if we cannot recover:
- dataset version URI
- code digest/container image
- hyperparameters/config
- artifacts location

