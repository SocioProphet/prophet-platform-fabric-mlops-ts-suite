# rdf-to-shir pack v0.1

Status: draft executable pack
Tracking issue: <https://github.com/SocioProphet/prophet-platform-fabric-mlops-ts-suite/issues/36>

## Purpose

This pack compiles a deterministic RDF/Turtle subset into Semantic Hyperknowledge Intermediate Representation (SHIR) JSON artifacts.

It is the first runtime slice behind the SHIR semantic and serialization contracts landed in:

- `SocioProphet/ontogenesis#27` — SHIR v0.1 semantic contract
- `SocioProphet/semantic-serdes#7` — SHIR schema/fixture slice
- `SocioProphet/semantic-serdes#8` — SHIR fixture validation workflow

## Contract

Input:

- Turtle fixture in the v0.1 supported subset.

Output:

- `candidate_assertion.json`
- `assertion.json`
- `receipt.json`

The pack intentionally does not emit PyG/DGL artifacts. Graph-ML lowering belongs in the `shir-to-pyg` pack.

## Supported v0.1 Turtle subset

- `@prefix prefix: <iri#> .`
- simple subject-predicate-object triples
- prefixed IRIs
- quoted string literals for labels
- `rdfs:label`
- object-property triples

The v0.1 fallback parser is deliberately narrow so the pack can run with Python stdlib only. A later implementation can add `rdflib` behind the same output contract.

## Run

```bash
python packs/rdf-to-shir/tools/rdf_to_shir.py \
  --input packs/rdf-to-shir/fixtures/topolvm.ttl \
  --out-dir /tmp/rdf-to-shir-out
```

Optional validation against a checked-out `semantic-serdes` schema directory:

```bash
python packs/rdf-to-shir/tools/rdf_to_shir.py \
  --input packs/rdf-to-shir/fixtures/topolvm.ttl \
  --out-dir /tmp/rdf-to-shir-out \
  --schema-dir ../semantic-serdes/schemas
```

## Governance boundaries

- Candidate assertions are not promoted directly to canonical truth.
- Assertions emitted by this pack are fixture-grade `VALIDATED` assertions, not ontogenesis promotion decisions.
- Blank-node handling is deferred beyond the v0.1 Turtle subset.
- Named graph/TriG context mapping remains a v0.2 implementation target.
- No proprietary IBM Hyperknowledge runtime dependency is introduced.

## Follow-up

Next packs should enforce semantic leakage detection and projection-loss reporting before SHIR artifacts are lowered into graph-ML or retrieval representations.
