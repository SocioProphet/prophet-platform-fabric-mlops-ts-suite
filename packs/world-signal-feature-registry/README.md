# World Signal Feature Registry Pack v0.1

Status: draft pack skeleton

## Purpose

Registers governed world-signal features before they are used by model pipelines.

## Inputs

- Feature registry JSON contract objects from `prophet-core-contracts`.
- Source manifests and provenance requirements.
- Optional Gaia ontology references.

## Outputs

- Feature registry manifest.
- Validation receipt.
- Promotion-readiness summary.

## Gates

- Contract exists.
- Feature ID is stable and namespaced.
- Provenance requirements are declared.
- Promotion state is explicit.

## Boundaries

- No model training.
- No ontology promotion by default.
- No ungoverned feature-store writes.
