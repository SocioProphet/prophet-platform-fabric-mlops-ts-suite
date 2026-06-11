# ACR Graph ML Pack v0.1

Status: draft pack skeleton

## Purpose

Evaluates Authority Concordance Rex entity-resolution and graph-ML paths under governed projection, leakage, and replay gates.

## Inputs

- Canonical entity graph.
- Source records.
- Concordance links.
- Decision ledger entries.
- Relationship edges.

## Outputs

- Graph projection manifest.
- Projection-loss report.
- Semantic-leakage report.
- Resolver evaluation receipt.

## Gates

- False-merge check.
- False-split check.
- Projection-loss report required.
- Semantic-leakage report required.
- Resolver policy version pinned.

## Boundaries

- No auto-merge on low confidence.
- No graph tensor materialization without projection receipt.
- No canonical promotion without ledger decision.
