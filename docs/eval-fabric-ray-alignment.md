# Eval Fabric ↔ Ray Lifecycle Alignment

## Purpose

This note records how the governed evaluation fabric in `SocioProphet/prophet-platform` aligns with the Ray / KubeRay deployment baseline in this repository.

## Why this repo matters

`prophet-platform` owns the executable eval-fabric runtime, provenance routes, competition views, and downstream suite consumption.

This repository owns the multi-cluster deployment baseline and the standard Ray Train / Ray Serve operational substrate. The two repos should remain distinct but explicitly aligned.

## Alignment map

| Eval-fabric concern | Canonical runtime repo | Canonical deployment repo | Notes |
|---|---|---|---|
| route, provenance, dossier, competition APIs | `SocioProphet/prophet-platform` | referenced here | runtime behavior lives downstream in platform |
| logical-statistical suite fixtures and tests | `SocioProphet/prophet-platform` | referenced here | deployment repo should not duplicate test semantics |
| training / tuning / serving substrate | referenced from platform | `SocioProphet/prophet-platform-fabric-mlops-ts-suite` | Ray/KubeRay lifecycle baseline belongs here |
| promotion / rollback operational context | runtime emits/tests downstream | deployment and rollout policy context belongs here | rollout semantics should remain compatible with eval-fabric artifact expectations |

## Ray lifecycle expectations

The deployment baseline should remain compatible with these lifecycle stages:
- `ray_data_prepare`
- `ray_train_fit`
- `ray_tune_search`
- `benchmark_evaluate`
- `ray_serve_promote`

These names are already used in downstream eval-fabric fixtures and should remain stable or be versioned explicitly if changed.

## Promotion and rollback

The deployment baseline should preserve a clear place for:
- promotion decision artifacts
- rollback readiness artifacts
- benchmark reports
- evidence receipts and event envelopes emitted by downstream runtime lanes

## Scope rule

This repository SHOULD define deployment and runtime substrate expectations.

It SHOULD NOT redefine the upstream logical-statistical, gating, graduation, or evidence profiles that already belong in `socioprophet-agent-standards`, nor the downstream eval-fabric API/test semantics that already belong in `prophet-platform`.

## Status

Captured as a deployment-alignment note. Not yet linked from the MLOps docs index.
