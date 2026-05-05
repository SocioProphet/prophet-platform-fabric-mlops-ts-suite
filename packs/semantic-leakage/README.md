# semantic-leakage pack v0.1

Status: draft executable pack
Tracking issue: <https://github.com/SocioProphet/prophet-platform-fabric-mlops-ts-suite/issues/38>

## Purpose

This pack detects semantic leakage in SHIR-derived graph/retrieval/ML projection manifests.

It prevents inflated model performance caused by ontology labels, graph partitions, source filenames, future timestamps, provenance fields, target-property leakage, naming conventions, and train/test contamination.

## Inputs

- A graph/retrieval/ML projection manifest JSON, such as the `pyg_manifest.json` emitted by `packs/shir-to-pyg`.
- Optional semantic-serdes schema directory for validating emitted `ProjectionLossReport` and `Receipt` artifacts.

## Outputs

- `semantic_leakage_report.json`
- `projection_loss_report.json`
- `receipt.json`
- `compile_error.json` on failure

The `projection_loss_report.json` carries a semantic-serdes-compatible `semantic_leakage` block, allowing this detector to plug into existing SHIR projection governance.

## Run

Clean fixture:

```bash
python packs/semantic-leakage/tools/semantic_leakage.py \
  --manifest packs/semantic-leakage/fixtures/clean_pyg_manifest.json \
  --out-dir /tmp/semantic-leakage-clean
```

Leaking fixture with fail-closed behavior:

```bash
python packs/semantic-leakage/tools/semantic_leakage.py \
  --manifest packs/semantic-leakage/fixtures/leaking_pyg_manifest.json \
  --out-dir /tmp/semantic-leakage-leaking \
  --prediction-cutoff 2026-01-01T00:00:00Z \
  --fail-on-blocking
```

Optional validation:

```bash
python packs/semantic-leakage/tools/semantic_leakage.py \
  --manifest packs/semantic-leakage/fixtures/clean_pyg_manifest.json \
  --out-dir /tmp/semantic-leakage-clean \
  --schema-dir ../semantic-serdes/schemas
```

## v0.1 leakage markers

- `RDF_TYPE_LABEL`
- `ONTOLOGY_HIERARCHY`
- `GRAPH_PARTITION`
- `SOURCE_FILENAME`
- `FUTURE_TIMESTAMP`
- `PROVENANCE_FIELD`
- `NAMING_CONVENTION`
- `TARGET_PROPERTY`
- `TRAIN_TEST_CONTAMINATION`

## Boundaries

- This pack does not train a model.
- This pack does not repair features automatically.
- This pack does not decide ontology promotion.
- This pack can run without PyTorch, PyG, DGL, or an LLM runtime.
