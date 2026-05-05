# SHIR governed chain v0.1

Status: draft executable chain

## Purpose

This chain proves the first governed SHIR graph-ML path end to end:

```text
rdf-to-shir -> shir-to-pyg -> semantic-leakage -> chain receipt
```

It uses the TopoLVM fixture and preserves receipts at every stage. The chain is intentionally manifest-only and does not import PyTorch, PyG, DGL, or an LLM runtime.

## Inputs

- Turtle fixture, defaulting to `packs/rdf-to-shir/fixtures/topolvm.ttl`.
- Optional semantic-serdes schema directory for validating SHIR-compatible outputs.

## Outputs

The chain writes stage outputs under the requested output directory:

```text
out/
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

## Run

```bash
python packs/shir-governed-chain/tools/run_shir_chain.py \
  --out-dir /tmp/shir-governed-chain
```

With semantic-serdes validation:

```bash
python packs/shir-governed-chain/tools/run_shir_chain.py \
  --out-dir /tmp/shir-governed-chain \
  --schema-dir ../semantic-serdes/schemas
```

## Guarantees

- RDF/Turtle input compiles into SHIR candidate/assertion/receipt artifacts.
- SHIR assertion lowers into a PyG-style manifest using relation-node preservation.
- Projection-loss report is emitted before graph-ML export artifacts are accepted.
- Semantic-leakage report is emitted after PyG manifest generation.
- The final chain receipt summarizes source hash, SHIR assertion hash, PyG manifest hash, projection-loss hash, semantic-leakage hash, policy decision, and replay metadata.

## Boundaries

- No tensor materialization.
- No GNN training.
- No ontology promotion.
- No automatic leakage repair.
- No proprietary Hyperknowledge runtime dependency.

## Completion estimate

This chain makes the workstream demo-complete but not production-complete. Production still needs full RDF parsing, named graph/TriG support, SHACL-linked promotion gates, richer projection manifests, tensor materialization, and cross-repo AgentPlane orchestration.
