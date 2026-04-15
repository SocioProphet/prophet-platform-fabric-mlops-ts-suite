# Prophet time-series library map (recommended OSS building blocks)

Prophet is a platform — we use open-source engines behind Prophet contracts.

This map is intentionally conservative: widely used, permissive, production-friendly projects.

---

## Classical forecasting / statistics

- **statsmodels**
  - ARIMA/SARIMA/SARIMAX
  - VAR/VARMAX
  - state-space models
  - (good for baselines + interpretable models)

- **sktime** (optional)
  - unified time-series API; many classical and ML forecasters
  - good for breadth, but choose a subset for production

---

## Volatility / risk (finance-specific)

- **arch**
  - ARCH/GARCH, EGARCH, GJR, Student-t distributions
  - a common Python standard for volatility modeling

- EVT / tails
  - can be done with SciPy / stats libraries, or custom implementations
  - kept as an “add-on” because it’s easy to misuse without careful validation

---

## Tree/ML workhorses

- **scikit-learn** (baseline)
  - lag-feature models (HistGradientBoostingRegressor, RandomForest, etc.)
  - fast to iterate and deploy

- Optional “pro” OSS engines (swap-in behind the same interface)
  - XGBoost / LightGBM / CatBoost

---

## Deep forecasting

- **PyTorch** (default deep runtime)
  - seq2seq (GRU/LSTM)
  - transformer baselines
  - export via TorchScript/ONNX if needed later

- Optional deep TS frameworks (evaluate before adopting)
  - GluonTS (probabilistic forecasting ideas)
  - PyTorch Forecasting (TFT-style models)
  - Darts (broad model zoo)

Prophet should treat these as **engines**, not as platform identity.

---

## Serving

- **Ray Serve / KubeRay**: flexible Python-native serving
- **KServe**: standardized InferenceService CRDs
- **Seldon Core 2**: alternative serving/MLOps framework

Prophet contract stays stable regardless.

