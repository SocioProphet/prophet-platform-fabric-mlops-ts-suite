# Decision-Grade World Signal MLOps Integration

Status: integration note v0.1
Owning repo: Prophet Platform Fabric MLOps TS Suite
Related repos: `SocioProphet/gaia-world-model`, `SocioProphet/prophet-core-contracts`, `SocioProphet/prophet-core-ledger`

## Purpose

This note maps governed world signals into Prophet MLOps. It covers foot-traffic/weather feature evaluation, entity-resolution energy ledgers, graph-ML concordance use cases, and human-behavior assessment models that require strict evaluation gates.

The repository already defines a governed semantic-to-graph-ML chain:

```text
rdf-to-shir -> shir-to-pyg -> semantic-leakage -> chain receipt
```

Decision-grade world signals should plug into that posture: semantic contract integrity first, projection-loss accounting second, leakage detection third, and replayable receipts before materialized training.

## Signal classes

### 1. Foot-traffic + weather time-series features

Primary model problem:

- predict or nowcast outcome variables using normalized mobility features and weather confounders.

Core feature groups:

- `FTI_daily` as normalized observed-population share;
- weather forecasts with temporal grain, horizon, cadence, spatial type, and resolution;
- POI mapping version and denominator-population definition as required metadata;
- holiday, event, and seasonality controls where available.

Required gates:

- leakage-safe train/test split relative to target-reporting dates;
- POI-set version stability report;
- denominator-population drift report;
- weather feature freshness report;
- backtest by sector/domain/geography;
- confidence interval or uncertainty band for decision use.

### 2. ACR entity concordance and graph-ML

Primary model problem:

- candidate generation, link prediction, entity deduplication, hierarchy inference, and confidence-ranked concordance.

Required inputs:

- `CanonicalEntity`;
- `SourceRecord`;
- `ConcordanceLink`;
- `AttributeAssertion`;
- `DecisionLedgerEntry`;
- `RelationshipEdge`.

Required gates:

- false-merge and false-split evaluation;
- high-ambiguity bucket reporting;
- projection-loss report when RDF/ontology data is projected into graph-ML tensors;
- semantic-leakage report preventing label leakage from authority identifiers or post-decision fields;
- replay receipt keyed by resolver run and policy version.

### 3. Energy-resolution ledgers

Energy-resolution entries are model-evaluation data as well as governance data. They expose the separation between top and runner-up candidates and perturbation stability.

MLOps use:

- train ambiguity classifiers;
- calibrate promotion thresholds;
- evaluate stability under perturbation;
- detect high-risk resolver regimes;
- create steward-review queues.

Required gates:

- distribution summary with at least 30 examples before statistical claims;
- low-margin bucket enumeration when <=10 examples;
- flip-rate threshold policy;
- calibration curve for threshold -> precision/recall;
- policy impact diff before threshold changes.

### 4. AI interview, personality, and leadership assessment models

The uploaded research corpus includes single-modality apparent personality prediction, transcript-based personality/job-screening estimation, and zero-shot leadership interview assessment. These belong in MLOps as benchmark and governance patterns, not as unreviewed production claims.

Required gates:

- human-in-the-loop evaluation;
- fairness evaluation across demographic groups where data exists;
- prompt/version pinning for LLM assessments;
- expert-rating rubric provenance;
- score-fit calibration;
- model card with explicit limitation language;
- no automated high-stakes decision without review.

## Contract dependencies

This repo should consume, not own, the shared schemas:

- `FeatureRegistryEntry` from `prophet-core-contracts`;
- `EnergyLedgerEntry` from `prophet-core-contracts`;
- `ConcordanceLink` from `prophet-core-contracts`;
- `DecisionLedgerEntry` from `prophet-core-contracts`;
- `ProofArtifact` from `prophet-core-contracts`.

The implementation should emit chain receipts compatible with the existing governed manifest chain.

## Suggested packs

Add packs only when examples and validation are ready:

- `packs/world-signal-feature-registry/`
- `packs/fti-weather-backtest/`
- `packs/acr-graph-ml/`
- `packs/energy-ledger-calibration/`
- `packs/assessment-hitl-eval/`

Each pack should include:

- manifest;
- schema references;
- fixture data;
- validation script;
- generated receipt;
- documentation of known failure modes.

## Acceptance criteria

A decision-grade world-signal model path is acceptable when it provides:

1. contract-valid inputs;
2. provenance-pinned source manifests;
3. evaluation gates appropriate to the signal class;
4. leakage and projection-loss checks where semantic graphs are projected;
5. replayable receipt;
6. explicit policy decision for whether outputs are evidence-only, review-required, or promoted.
