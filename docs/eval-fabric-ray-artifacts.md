# Eval Fabric Ray Artifact Outputs

## Purpose

This note records the expected Ray-side artifact outputs that should stay compatible with the governed eval-fabric runtime and its downstream suite expectations.

## Why this matters

`prophet-platform` now carries fixture and test coverage for:
- promotion decisions
- rollback records
- gate activation records
- graduation records
- lifecycle artifact graphs
- live lifecycle-bundle runtime output

This repository should make clear how RayJob and RayService workflows relate to those artifact expectations without redefining the downstream runtime semantics.

## Expected Ray-facing artifact classes

For runs that participate in governed promotion, the Ray lifecycle SHOULD be able to produce or hand off references for:
- `benchmark_report`
- `promotion_decision`
- `rollback_record`
- `event_envelope`
- `evidence_receipt`

## RayJob / RayService relationship

### RayJob side

RayJob-oriented workflows SHOULD provide:
- dataset version reference
- training run ID
- tuning search ID if applicable
- benchmark report reference
- model artifact reference

### RayService side

RayService-oriented workflows SHOULD provide:
- serving target reference
- promoted model version reference
- rollout status reference
- rollback readiness context

## Compatibility rule

The Ray-side artifact vocabulary does not need to emit identical file layouts to the eval-fabric runtime, but it SHOULD preserve stable semantic references so the downstream runtime and suites can connect:
- recipe / training context
- promotion decision
- rollback readiness
- benchmark evidence

## Current lifecycle names to preserve

The following lifecycle names are already used in downstream eval-fabric fixtures and tests and should remain stable unless explicitly versioned:
- `ray_data_prepare`
- `ray_train_fit`
- `ray_tune_search`
- `benchmark_evaluate`
- `ray_serve_promote`

## Status

Captured as a narrow deployment-side artifact note. Not yet linked from `docs/mlops-ray.md` or any workflow example.
