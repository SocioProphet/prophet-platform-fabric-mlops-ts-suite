# Prophet Time-Series Model Families (what we support)

This document answers: **what time-series model families should Prophet support** (for finance-grade forecasting,
risk, and trading systems), and how those families map to Prophet’s training/serving workflow.

Philosophy: Prophet is a **platform**. We support a **portfolio** of model families because:
- no single family dominates across horizons/regimes/assets,
- finance data is non-stationary and adversarial (your edge decays),
- you need baselines and interpretable models for governance,
- and you need deep models for representation learning and multi-series scaling.

---

## 0) Canonical time-series tasks (Prophet contracts)

Prophet should treat “time series” as multiple related tasks:

### A) Forecasting (point + probabilistic)
- next-step, multi-step (horizon H)
- direct vs recursive vs multi-output forecasting
- probabilistic: quantiles / predictive distributions

### B) Volatility / risk forecasting
- conditional variance (σ²), realized vol, tail risk (VaR/CVaR)
- correlation/covariance forecasting (portfolio + hedging)

### C) Regime detection / change points
- market regimes, structural breaks, volatility regimes
- change-point detection, switching dynamics

### D) Event / intensity modeling (microstructure)
- point processes (Hawkes), trade arrivals, order flow intensity

### E) Representation learning (multi-series)
- learn embeddings for symbols/tenants/strategies
- transfer learning and foundation models

### F) Anomaly detection and monitoring
- outliers, feed issues, drift, “something changed”

Prophet’s interfaces should be task-first, not “model-first.”

---

## 1) Support tiers (how we ship this without drowning)

### Tier 0: baselines (always supported)
These are mandatory for honest evaluation:
- Naive / seasonal naive
- EWMA / moving average baselines
- “last value” baselines for some financial series
- simple linear regression with lag features

### Tier 1: classical forecasting/statistics (interpretable, fast)
**Univariate:**
- AR / MA / ARMA / ARIMA / SARIMA
- ETS / exponential smoothing (incl. Holt-Winters)
- STL decomposition + forecast residuals
- Prophet-style additive models (trend + seasonality + regressors)

**State space / filtering:**
- Kalman filter models
- local level / local trend
- dynamic regression with time-varying coefficients

**Multivariate:**
- VAR / VARMA / VARMAX
- VECM / cointegration models (pairs/relative value)

Why Tier 1 matters in finance:
- interpretability and governance,
- fast iteration,
- strong baselines for many horizons.

### Tier 2: volatility & heavy-tail families (finance-specific)
This is where “ARCH/GARCH and friends” live.

**ARCH/GARCH family:**
- ARCH, GARCH
- EGARCH (asymmetric effects)
- GJR-GARCH / TGARCH (leverage effects)
- FIGARCH / HYGARCH (long memory)
- GARCH with Student-t / skewed distributions
- GARCH-in-mean (if needed)

**Multivariate volatility/correlation:**
- DCC-GARCH (time-varying correlations)
- BEKK (heavier, but exists)
- dynamic factor volatility models

**Realized volatility models:**
- HAR-RV (heterogeneous autoregressive realized volatility)
- realized-GARCH variants (if you go deep on intraday)

**Tail models:**
- EVT / GPD for tail risk
- quantile regression for VaR

Why Tier 2 is non-negotiable:
- options and risk systems care more about volatility/correlation than mean returns,
- heavy tails and asymmetry are the default, not an edge case.

### Tier 3: machine learning “tabularized time series”
The biggest ROI-per-engineering-hour category.

Approach: turn time series into supervised learning with features:
- lags, rolling stats, seasonal features
- microstructure features (spreads, imbalance, volatility estimators)
- cross-series aggregates

Models:
- gradient boosting (XGBoost/LightGBM/CatBoost style)
- random forests / extra trees
- linear models with regularization (Lasso/Elastic Net)
- quantile regression forests / quantile boosting for uncertainty

Why Tier 3 matters:
- strong performance on noisy series,
- easy to interpret with feature attribution,
- easy to deploy,
- extremely competitive as a default.

### Tier 4: deep sequence models (RNN/seq2seq/TCN/Transformers)
This is where your “recurrent nets and seq2seq” request lands.

**RNN family:**
- vanilla RNN (rare)
- LSTM / GRU
- bidirectional variants for encoding
- attention over RNN outputs

**Seq2Seq (encoder-decoder)**
- classic seq2seq with attention (multi-step)
- “temporal encoder” + “horizon decoder”
- optionally with covariates and static features

**Temporal CNN family:**
- TCN (temporal convolutional networks)
- WaveNet-like dilated convolutions
- 1D CNN hybrids (esp. for order book signals)

**Transformer family:**
- attention models for long context
- variants optimized for time series (patching, frequency-domain, decomposition)
- temporal fusion styles (covariates + gating + attention)

Why Tier 4 matters:
- multi-series learning (thousands of symbols),
- complex nonlinear dependencies,
- representation learning that can transfer.

### Tier 5: modern “global” forecasting models & foundation models
This is the “pretrain once, adapt everywhere” layer.

Families to support:
- global probabilistic forecasting (DeepAR-like conceptually)
- N-BEATS / N-HiTS style basis-function models
- transformer-based global forecasters
- foundation models trained on large corpora of time series (if/when you choose)

Why Tier 5 matters:
- one model can serve many symbols/tenants,
- fast adaptation, less per-asset training,
- can become a product moat.

### Tier 6: specialized finance surfaces & structured objects (options, curves)
Prophet should support time series that are actually **structured manifolds**:

**Implied volatility surfaces (IVS):**
- parametric surface models (SVI / SABR style parameterizations)
- surface as a function of (strike, maturity) evolving in time
- constraints: no-arbitrage conditions, monotonicity, convexity

**Yield curves / term structure:**
- Nelson–Siegel / Svensson style
- dynamic term structure models
- PCA / factor models over curves

**Cross-asset graphs:**
- correlation networks, factor graphs
- regime-dependent graphs
- these naturally connect to your neuro-symbolic “domain constraints” story

---

## 2) What Prophet should standardize as “model interfaces”

To make all these families plug into one workflow, Prophet needs 3 standard interfaces:

### 2.1 ForecastModel interface
- `fit(dataset_version, features_spec, horizon, loss_spec)`
- `predict(context_window, horizon) -> {mean, quantiles, distribution_params}`
- `explain(...)` (optional but encouraged)
- `diagnostics(...)` (residuals, stability, calibration)

### 2.2 RiskModel interface
- `fit(...)`
- `predict_vol(...)`, `predict_var(...)`, `predict_cvar(...)`
- supports distributional outputs and tail modeling

### 2.3 Simulator / Generator interface (optional but powerful)
- `sample_paths(n, horizon)` for scenario generation
- used for stress tests, options pricing workflows, risk simulations

Prophet’s registry stores:
- model artifact URI(s)
- dataset version URI
- code digest (container)
- hyperparams + training config
- evaluation report + gates
- promotion history

---

## 3) Serving modes (how models show up in production)

Prophet should support three serving modes consistently:

1) **Online inference**
- low latency
- runs behind prophet-query-gateway policy + audit

2) **Nearline / batch inference**
- scheduled forecasts (e.g., every minute/hour/day)
- writes forecasts into lake + ClickHouse for downstream consumption

3) **Streaming inference**
- consumes event streams and updates state continuously
- often used for volatility state or microstructure signals

Ray Serve is one serving engine; KServe/Seldon are alternatives. Prophet keeps the contract.

---

## 4) Model selection guidance (finance reality)

A practical default stack for an initial “finance-grade time series suite”:

**For mean forecasts (returns/price deltas):**
- Tier 0 baselines + Tier 3 ML (GBMs) as the default workhorses
- Tier 1 ARIMA/ETS for interpretability and fast baselines
- Tier 4 deep models only when you have enough data volume and a clear win

**For volatility/risk:**
- Tier 2 GARCH-family + HAR-RV style baselines
- deep models as add-ons (often as “features into risk models”)

**For multi-series scaling:**
- Tier 5 global models once you’ve proven data quality + governance.

---

## 5) Metrics & evaluation (what Prophet should natively report)

Prophet should compute and persist:

**Forecast accuracy:**
- MAE, RMSE
- sMAPE (with care)
- MASE (robust across series)
- pinball loss for quantiles
- CRPS (for full distributions)

**Calibration / uncertainty:**
- quantile coverage
- PIT histograms (probability integral transform)

**Finance-specific backtest metrics (downstream):**
- Sharpe / Sortino
- max drawdown
- turnover / transaction cost sensitivity
- tail risk measures (VaR/CVaR stability)

**Stability checks:**
- walk-forward validation (rolling windows)
- regime robustness (evaluate across regimes)
- leakage audits (point-in-time)

---

## 6) How this maps to Prophet MLOps (train → gate → serve)

- Data versioning and manifests come from Prophet durability plane.
- Training is scheduled by Prophet workflows (Argo or equivalent).
- Training engines can be RayJob, SparkApplication, or K8s Job.
- Artifacts and reports go to object storage.
- Registry is MLflow or Prophet-native.
- Serving is RayService or KServe/Seldon.

See:
- `docs/mlops-ecosystem.md`
- `docs/mlops-ray.md`

---

## 7) Recommended “first implementation wave” (ship fast)

If you want a crisp, shippable first wave:

1) Tier 0 baselines
2) Tier 1 ARIMA/ETS/state-space (fast, interpretable)
3) Tier 2 GARCH family (ARCH/GARCH/EGARCH/GJR + Student-t)
4) Tier 3 GBM-based forecasters (tabular features)
5) Tier 4 LSTM/GRU seq2seq (one strong deep baseline)
6) Tier 4 transformer baseline (one strong global baseline)
7) Tier 6 IV surface parameterization (SVI-like) if options is core

Everything else is an incremental add-on once the platform contracts are proven.

