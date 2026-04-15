# Prophet time-series Argo workflows (reference)

These are *reference* Argo WorkflowTemplates for running Prophet time-series training pipelines.

They assume:
- you have Argo Workflows installed in `prophet-workflows`
- you configured an artifact repository (S3/MinIO) for storing artifacts/logs
- the training images contain the Prophet Time Series SDK (`sdk/prophet_ts`)

Templates:
- `ts-train-eval-deploy-template.yaml`: basic train → eval → (optional) deploy flow

These templates are intentionally minimal and should be adapted to:
- your secret management (External Secrets)
- your RBAC and GitOps approach (Argo CD)
- your registry choice (MLflow or Prophet-native)

