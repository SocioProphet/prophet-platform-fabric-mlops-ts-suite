# FTI Weather Backtest Pack v0.1

Status: draft pack skeleton

## Purpose

Evaluates foot-traffic index features with weather covariates using leakage-safe time-series backtests.

## Inputs

- FTI daily features.
- Weather features.
- POI-set version metadata.
- Denominator-population definition metadata.
- Target outcome time series.

## Outputs

- Backtest manifest.
- Leakage report.
- Drift report.
- Evaluation receipt.

## Gates

- Target-date leakage check.
- POI-set version stability check.
- Denominator drift check.
- Weather freshness check.
- Train/test split manifest present.

## Boundaries

- No investment recommendation.
- No production scoring without receipt.
- No causal claim without separate causal design.
