# Prophet model images (reference)

These Dockerfiles are *reference* training/serving images for common time-series model families.
They are designed to be used by:
- RayJobs (distributed training)
- Kubernetes Jobs (classical models)
- Spark jobs (feature engineering)

Guiding principle: **bake dependencies into the image** for reliability and repeatability.

Images included:
- `prophet-models-classical`: ARIMA/ETS/state-space style baselines (statsmodels)
- `prophet-models-garch`: ARCH/GARCH volatility models (`arch` library)
- `prophet-models-deep`: seq2seq + transformer baselines (PyTorch)
- `prophet-models-surfaces`: options surfaces (SVI/SABR-style placeholders)

These images are not “complete products” — they are scaffolding that shows
how Prophet model specs become artifacts and metrics.

