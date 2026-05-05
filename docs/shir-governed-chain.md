# SHIR Governed Chain v0.1

Status: draft executable demo chain
Pack: `packs/shir-governed-chain/`

## Purpose

The SHIR governed chain proves the first end-to-end semantic-to-graph-ML manifest path with governance receipts and safety gates.

```text
rdf-to-shir -> shir-to-pyg -> semantic-leakage -> chain receipt
```

The chain is intentionally manifest-only. It does not import PyTorch, PyG, DGL, or an LLM runtime. The goal is to prove semantic contract integrity, projection-loss accounting, semantic-leakage detection, and replayable receipts before tensor materialization or training.

## Stage map

| Stage | Pack | Input | Output | Gate |
| --- | --- | --- | --- | --- |
| 1 | `packs/rdf-to-shir` | Turtle fixture | SHIR candidate/assertion/receipt | semantic-serdes schema validation |
| 2 | `packs/shir-to-pyg` | SHIR assertion | PyG-style manifest/projection manifest/receipt | relation-node preservation |
| 3 | `packs/projection-loss-report` | SHIR assertion + projection manifest | projection-loss report/receipt | no silent semantic flattening |
| 4 | `packs/semantic-leakage` | PyG-style manifest | semantic-leakage report/projection-loss report/receipt | leakage and training/export policy gate |
| 5 | `packs/shir-governed-chain` | stage artifacts | `chain_run_receipt.json` | replayable chain-level receipt |

## Run locally

```bash
python packs/shir-governed-chain/tools/run_shir_chain.py \
  --out-dir /tmp/shir-governed-chain
```

With semantic-serdes schema validation:

```bash
python packs/shir-governed-chain/tools/run_shir_chain.py \
  --out-dir /tmp/shir-governed-chain \
  --schema-dir ../semantic-serdes/schemas
```

## Output layout

```text
/tmp/shir-governed-chain/
  rdf-to-shir/
    candidate_assertion.json
    assertion.json
    receipt.json
  shir-to-pyg/
    pyg_manifest.json
    projection_manifest.json
    projection_loss_report.json
    receipt.json
  semantic-leakage/
    semantic_leakage_report.json
    projection_loss_report.json
    receipt.json
  chain_run_receipt.json
```

## Acceptance assertions

The CI workflow `validate-shir-governed-chain` asserts that:

- SHIR candidate/assertion/receipt artifacts are emitted.
- PyG-style manifest artifacts are emitted.
- Projection-loss accounting is present.
- Semantic-leakage detection is present.
- Relation-node projection preserves the n-ary connector semantics.
- The TopoLVM fixture has clean semantic-leakage risk.
- The final chain receipt validates against semantic-serdes `shir_receipt.schema.json`.

## Current completion estimate

This makes the SHIR workstream demo-chain complete, not production complete.

Approximate current status:

- Governed demo chain: 90 percent complete.
- Credible governed SHIR MVP: 65 percent complete.
- Production-grade SHIR/GML fabric: 35 percent complete.

Remaining demo polish:

1. AgentPlane orchestration handoff.
2. Additional fixture coverage beyond TopoLVM.
3. Public operator-facing runbook and troubleshooting notes.

Remaining production work:

1. Full RDF parser support using a proper RDF library behind the same contract.
2. TriG/named graph and RDF-star metadata support.
3. SHACL-linked promotion gates from ontogenesis.
4. Tensor materialization and dataset manifests for PyG/DGL.
5. Signed receipts and publication gates.
6. AgentPlane job orchestration and artifact retention.
7. Larger leakage test corpus and regression fixtures.
