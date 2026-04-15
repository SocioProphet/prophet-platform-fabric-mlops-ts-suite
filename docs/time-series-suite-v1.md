# Prophet Time-Series Suite v1 (what we actually ship)

This is the “no hand-waving” plan for shipping a finance-grade time-series capability
as part of Prophet Platform.

The goal is not to “support every model.” The goal is:
- a strong baseline set,
- a volatility/risk set (options/risk shops care),
- and a modern deep baseline set for multi-series scaling,
all wrapped in Prophet’s reproducible train→gate→serve workflow.

---

## Suite v1: model packs

### Pack A: Forecasting Core (mean + quantiles)
**Families:**
- baselines (naive, seasonal naive, EWMA)
- ARIMA/SARIMA (interpretable classical)
- GBM-with-lags (default workhorse)
- one deep seq2seq baseline (GRU/LSTM + attention)
- one transformer baseline (global forecaster)

**Outputs:**
- point forecast + quantiles (0.1/0.5/0.9 by default)
- calibration checks (coverage)

**Serving modes:**
- nearline (write forecasts to ClickHouse)
- online (optional)

### Pack B: Volatility & Risk Core (ARCH/GARCH + realized vol)
**Families:**
- GARCH family (GARCH, EGARCH, GJR-GARCH) with Student-t
- HAR-RV baseline (realized volatility)
- optional EVT tail-fit (post-v1 add-on)

**Outputs:**
- volatility forecasts σ or σ²
- VaR/CVaR surfaces as an add-on once distributional modeling is proven

**Serving modes:**
- batch/nearline by default (risk systems often tolerate minutes)

### Pack C: Options Surface Core (structured time series)
**Families:**
- SVI-like surface parameterizations (placeholder in v1)
- constraints hooks (no-arbitrage checks)

**Outputs:**
- fitted surface parameters
- surface reconstruction APIs (strike,maturity → IV)

**Serving modes:**
- nearline fit + query

---

## The contract: everything is a spec + a run

Prophet treats each model as:
- a `ProphetModelSpec` (declarative)
- a dataset version URI
- a training run that produces:
  - artifacts
  - metrics
  - an evaluation report
  - a promotion decision

Example specs are in `model-specs/`.

---

## Training/serving engines (pluggable)

Default engine choices for v1:

- Training:
  - classical + GARCH: Kubernetes Job (fast, simple)
  - deep models: RayJob (GPU capable)

- Serving:
  - online: RayService (Ray Serve) OR KServe (optional)
  - nearline/batch: scheduled workflows writing to ClickHouse/lake

Prophet keeps the interface. Engines are replaceable.

---

## What is NOT in v1 (deliberately)

- full multivariate GARCH suites (DCC/BEKK) as a default
- foundation model pretraining across “everything”
- microstructure point-process models (Hawkes) as first-class

Those are v2+ once v1 contracts and data hygiene are proven.

