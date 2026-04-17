# Profit MPCC trading order lifecycle intake (v0)

## Purpose

This document stages the trading-order lifecycle note emerging from `mdheller/profit-mpcc` for review inside the platform fabric / MLOps / time-series suite lane.

## Why this matters here

The platform suite is the downstream deployment and MLOps lane. The upstream `profit-mpcc` line is semantic/archive work, but its governed order lifecycle has direct implications for:
- market-data normalization,
- signal-to-intent transition,
- approval and risk gating,
- execution report handling,
- position-state updates,
- reconciliation and compensation.

## Intake stance

This is a review copy for alignment inside the platform suite lane. It is not the canonical upstream source of truth.

Only stabilized deployment-facing and runtime-facing portions should eventually influence this repo.
