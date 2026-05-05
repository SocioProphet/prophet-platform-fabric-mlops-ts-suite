# shir-to-pyg pack v0.1

Status: draft executable pack
Tracking issue: <https://github.com/SocioProphet/prophet-platform-fabric-mlops-ts-suite/issues/37>

## Purpose

This pack lowers a SHIR assertion into a PyTorch Geometric-style heterogeneous graph manifest without importing PyTorch or PyG.

It is intentionally manifest-first. Runtime tensor materialization should come later, after the manifest contract is stable and governed by projection-loss and semantic-leakage gates.

## Inputs

- SHIR assertion JSON.
- Optional semantic-serdes schema directory for validating generated projection-loss and receipt artifacts.

## Outputs

- `pyg_manifest.json`
- `projection_manifest.json`
- `projection_loss_report.json`
- `receipt.json`
- `compile_error.json` on failure

## Run

```bash
python packs/shir-to-pyg/tools/shir_to_pyg.py \
  --source-shir packs/shir-to-pyg/fixtures/source_assertion.json \
  --out-dir /tmp/shir-to-pyg-out
```

Optional validation against a checked-out `semantic-serdes` schema directory:

```bash
python packs/shir-to-pyg/tools/shir_to_pyg.py \
  --source-shir packs/shir-to-pyg/fixtures/source_assertion.json \
  --out-dir /tmp/shir-to-pyg-out \
  --schema-dir ../semantic-serdes/schemas
```

## Design boundaries

- No PyTorch/PyG runtime dependency in v0.1.
- No training job in v0.1.
- No direct RDF parsing; input is SHIR.
- No semantic truth promotion; ontogenesis owns the semantic contract.
- No projection without a projection-loss report.

## Projection strategy

The default strategy is `relation_node`.

For an n-ary connector such as:

```text
provisions(provider, resource, target_context)
```

The pack emits a relation node and typed edge triplets:

```text
(Technology, role_provider, Relation)
(Relation, role_resource, StorageResource)
(Relation, role_target_context, ComputeNode)
(Relation, supported_by, DocumentAnchor)
(Relation, scoped_by, Context)
```

This keeps n-ary semantics recoverable in the manifest and avoids silent binary-edge collapse.

## Governance

This pack calls the projection-loss-report contract by emitting a `projection_manifest.json` and invoking `packs/projection-loss-report/tools/projection_loss_report.py`. The resulting `projection_loss_report.json` is copied into the pack output and referenced from the final `receipt.json`.

Semantic leakage metadata is included in the projection manifest as a first-class block, but the dedicated semantic-leakage detector pack remains the next enforcement layer.
