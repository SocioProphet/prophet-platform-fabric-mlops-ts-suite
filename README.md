# Prophet Platform Fabric (Multi-cluster + Multi-mesh baseline)

This repo is a standard Kubernetes “fabric” stack you can deploy in every region/edge cluster.

## Deploy (single cluster)

```bash
cd helm
helmfile apply
```

## Notes

- This is a baseline, not a finished product.
- For production you will want:
  - GitOps (Argo CD) driving Helmfile/Helm
  - locked versions + SBOM
  - resource tuning per environment
  - network policies + admission policies

See `docs/fabric-standard.md`.


## Atoms and pods we ship

See:
- `docs/atoms-catalog.md`
- `docs/pods-to-ship.md`
- `docs/profile-matrix.md`


## Prophet Hierarchy Tree (PHT)

See `docs/pht.md` for the canonical platform/app layering: Fabric → Prophet Platform → SocioProfit app.


## Ray Train + Ray Serve (MLOps)

See `docs/mlops-ray.md` for the standard Prophet model ops workflow aligned with KubeRay (RayJob/RayService).


## MLOps ecosystem add-ons (beyond Ray)

Ray is the default distributed runtime (Train + Serve) in the main `helm/helmfile.yaml`.

For a broader open-source MLOps toolchain, apply the optional Helmfiles:

- `helm/helmfile-mlops-core.yaml` (Argo Workflows, MLflow, Feast operator, Spark operator, OpenTelemetry operator)
- `helm/helmfile-ml-serving.yaml` (KServe, Seldon Core 2)
- `helm/helmfile-gpu.yaml` (NVIDIA GPU Operator)

See:
- `docs/mlops-ecosystem.md`
- `docs/mlops-ray.md`


## Time-series model families

See `docs/time-series-model-families.md` for the Prophet-supported time-series model taxonomy (ARIMA/ETS, ARCH/GARCH, RNN/seq2seq, transformers, foundation models, options surfaces, etc.) and how they map into Prophet MLOps.


## Time-series suite v1

See:
- `docs/time-series-suite-v1.md`
- `docs/time-series-eval-gates.md`
- `model-specs/` (example ProphetModelSpec YAMLs)
- `docker/` (reference training images)
- `workflows/` (Argo workflow templates)


## Time-series roadmap

See `docs/time-series-roadmap.md` for the time-series suite roadmap and pack plan.
See `docs/time-series-library-map.md` for recommended OSS engines behind Prophet time-series contracts.
