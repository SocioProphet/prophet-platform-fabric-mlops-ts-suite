# Prophet time-series roadmap (families & releases)

Prophet supports **multiple model families** because market data is non-stationary and “best model”
depends on horizon, regime, asset class, and operational constraints.

This roadmap is deliberately packaged as **packs** so Prophet can ship a coherent product while still
letting advanced teams bring their own engines.

---

## v1 (Suite v1) — ship fast, finance-grade baseline

**Forecasting Core**
- Baselines: naive / seasonal naive / EWMA
- ARIMA/SARIMA (per-series) for interpretability
- GBM with lag features (tree-based workhorse)
- Deep baseline: GRU “seq2seq-ish” multi-horizon model
- Deep baseline: transformer encoder multi-horizon model

**Volatility & Risk Core**
- ARCH/GARCH with asymmetric variants (EGARCH, GJR) + Student-t
- Simple realized-vol baseline: HAR-RV (as a next add-on; can be implemented as a linear model)

**What v1 proves**
- dataset version → reproducible training
- walk-forward evaluation + gating hooks
- artifact/registry integration
- online/nearline serving integration path (RayService/KServe)

---

## v1.1 — “serious stats” expansion (still pragmatic)

**State-space / filtering**
- Kalman filter models for dynamic regression
- local level / local trend
- time-varying coefficients (useful for drifting relationships)

**Multivariate classical**
- VAR / VARMAX
- VECM / cointegration (pairs / relative value)

**Volatility add-ons**
- FIGARCH / long-memory variants (where supported)
- DCC-GARCH (time-varying correlations) for portfolio/hedging contexts

---

## v2 — regime-aware + multi-series scaling

**Regime detection**
- change-point detection (offline + online)
- HMM / switching state-space models (regime switching)

**Global forecasting models**
- N-BEATS / N-HiTS style models
- probabilistic global models (DeepAR-like conceptually)

**Uncertainty done right**
- distributional forecasting (Student-t / mixture)
- CRPS + calibration tooling
- conformal prediction as an add-on (wraps any forecaster)

---

## v3 — market microstructure + structured finance objects

**Point processes / intensity**
- Hawkes processes for event intensity (trades, arrivals, order flow)

**Options & curves**
- implied vol surfaces as constrained dynamic objects (SVI/SABR parameterizations)
- yield curve dynamic models

**Neuro-symbolic constraints**
- enforce “domain rules” (no-arb, monotonicity, convexity) at training time and at inference time

---

## Non-negotiables (platform posture)

- Every pack must run in the same Prophet MLOps flow: train → eval → gate → promote → serve.
- Models are replaceable engines. Durability is not:
  - commit log + immutable lake manifests are the source of truth.
