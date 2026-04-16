# Relationship to Profit MPCC

## Purpose

This note records the current boundary between `SocioProphet/prophet-platform-fabric-mlops-ts-suite` and `mdheller/profit-mpcc`.

## Current stance

- `prophet-platform-fabric-mlops-ts-suite` is the downstream deployment / fabric baseline / MLOps / time-series suite lane.
- `profit-mpcc` is the upstream semantic/archive drafting root for conversational event fabric and the emerging trading-capable event/control model.

## What is not true

This repo is **not** the canonical home for the full MPCC archive line.

The suite should not absorb archive-native or still-moving semantic surfaces wholesale.

## Likely future influence surfaces

The strongest future influence from `profit-mpcc` is expected around:
- market-data event semantics,
- order / approval / execution / reconciliation chain semantics,
- governed partial-order event handling for real-time trading workloads.

## Governance rule

Treat `profit-mpcc` as an upstream drafting root and consume only narrow, stabilized tranches relevant to the platform suite lane.
