# Profit MPCC approval/reconciliation lifecycle intake (v0)

## Purpose

This note stages a narrow approval/reconciliation lifecycle slice from `mdheller/profit-mpcc` for review inside the platform fabric / MLOps / time-series suite lane.

## Why this matters here

The upstream MPCC line distinguishes:
- order intent,
- approval decision,
- execution report,
- position change,
- reconciliation variance,
- and compensation.

For the platform suite, that separation matters for:
- policy-aware orchestration,
- post-trade variance detection,
- remediation workflows,
- and time-series observability over governed trading state.

## Candidate platform-facing implications

- approval and reconciliation should remain distinct event families,
- variance and compensation should append history rather than overwrite state,
- post-trade remediation needs its own observability and policy labels.

## Intake stance

This is a review copy for alignment inside the platform suite lane. It is not the canonical upstream source of truth.
