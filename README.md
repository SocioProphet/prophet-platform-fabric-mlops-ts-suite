# Prophet Platform Fabric

This repository contains the multi-cluster and multi-mesh fabric baseline for Prophet Platform MLOps work.

## Deploy

```bash
cd helm
helmfile apply
```

## Notes

This is a baseline, not a finished product. Production deployments should use GitOps, locked versions, SBOMs, resource tuning, network policies, and admission policies.

See `docs/fabric-standard.md`.

## Atoms and pods we ship

See:

- `docs/atoms-catalog.md`
- `docs/pods-to-ship.md`
- `docs/profile-matrix.md`

## Prophet Hierarchy Tree

See `docs/pht.md` for the canonical platform and application layering.

## Ray Train and Ray Serve

See `docs/mlops-ray.md` for the standard Prophet model operations workflow aligned with KubeRay.

## MLOps ecosystem add-ons

Ray is the default distributed runtime in the main `helm/helmfile.yaml`.

For broader open-source MLOps support, see:

- `docs/mlops-ecosystem.md`
- `docs/mlops-ray.md`

## SHIR governed graph-ML manifest chain

The SHIR governed chain proves the first semantic-to-graph-ML manifest path with governance receipts and safety gates:

```text
rdf-to-shir -> shir-to-pyg -> semantic-leakage -> chain receipt
```

See:

- `docs/shir-governed-chain.md`
- `packs/rdf-to-shir/README.md`
- `packs/projection-loss-report/README.md`
- `packs/shir-to-pyg/README.md`
- `packs/semantic-leakage/README.md`
- `packs/shir-governed-chain/README.md`

The chain is manifest-only in v0.1. It exists to prove semantic contract integrity, projection-loss accounting, semantic-leakage detection, and replayable receipts before tensor materialization or training.

Run:

```bash
python packs/shir-governed-chain/tools/run_shir_chain.py --out-dir /tmp/shir-governed-chain
```

## Time-series model families

See `docs/time-series-model-families.md` for the Prophet-supported time-series model taxonomy and how it maps into Prophet MLOps.

## Time-series suite v1

See:

- `docs/time-series-suite-v1.md`
- `docs/time-series-eval-gates.md`
- `model-specs/`
- `docker/`
- `workflows/`

## Time-series roadmap

See `docs/time-series-roadmap.md` and `docs/time-series-library-map.md`.
