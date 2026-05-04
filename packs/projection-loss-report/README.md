# projection-loss-report pack v0.1

Status: draft executable pack
Tracking issue: <https://github.com/SocioProphet/prophet-platform-fabric-mlops-ts-suite/issues/39>

## Purpose

This pack audits a SHIR lowering operation and emits a semantic-serdes-compatible `ProjectionLossReport` plus `Receipt`.

It enforces the SHIR rule: no silent semantic flattening.

## Contract

Inputs:

- Source SHIR assertion JSON.
- Projection manifest JSON describing the target representation and preservation strategy.

Outputs:

- `projection_loss_report.json`
- `receipt.json`
- `compile_error.json` on failure

## Run

```bash
python packs/projection-loss-report/tools/projection_loss_report.py \
  --source-shir packs/projection-loss-report/fixtures/source_assertion.json \
  --projection-manifest packs/projection-loss-report/fixtures/lossy_pyg_manifest.json \
  --out-dir /tmp/projection-loss-out
```

Optional validation against a checked-out `semantic-serdes` schema directory:

```bash
python packs/projection-loss-report/tools/projection_loss_report.py \
  --source-shir packs/projection-loss-report/fixtures/source_assertion.json \
  --projection-manifest packs/projection-loss-report/fixtures/lossy_pyg_manifest.json \
  --out-dir /tmp/projection-loss-out \
  --schema-dir ../semantic-serdes/schemas
```

Blocking mode:

```bash
python packs/projection-loss-report/tools/projection_loss_report.py \
  --source-shir packs/projection-loss-report/fixtures/source_assertion.json \
  --projection-manifest packs/projection-loss-report/fixtures/blocking_pyg_manifest.json \
  --out-dir /tmp/projection-loss-blocking \
  --fail-on-blocking
```

A blocking run still writes report artifacts, then exits with code `2`.

## v0.1 loss dimensions

- `N_ARY_RELATION`
- `TEMPORAL_SCOPE`
- `OBSERVATION_TIME`
- `EVIDENCE_ANCHOR`
- `POLICY_SCOPE`
- `CONTEXT`
- `CURATION_STATE`
- `NOISE_ASSESSMENT`

## Boundaries

- This pack audits projection manifests; it does not execute graph-ML projection.
- No PyTorch, PyG, DGL, or proprietary Hyperknowledge runtime dependency is required.
- Blocking findings stop downstream publication only when callers opt into `--fail-on-blocking`.
- Ontology mutation and promotion remain outside this pack.
