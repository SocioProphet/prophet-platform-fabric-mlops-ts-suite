# Relationship to TritFabric

## Purpose

This note records the boundary between `SocioProphet/prophet-platform-fabric-mlops-ts-suite` and `SocioProphet/tritfabric`.

## Boundary summary

- `tritfabric` is the consolidated fabric / bridge / runtime-and-governance working tree.
- `prophet-platform-fabric-mlops-ts-suite` is the deployable Prophet Platform fabric baseline and MLOps/time-series suite lane.

## Implication

This repository should be treated as a downstream platform deployment and suite repo adjacent to `tritfabric`, not as a replacement for the canonical fabric/bridge constitutional lane.

## Workspace controller

The canonical workspace and registry integration for this repository belongs in `SocioProphet/sociosphere`.
