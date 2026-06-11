# Energy Ledger Calibration Pack v0.1

Status: draft pack skeleton

## Purpose

Calibrates entity-resolution and extraction promotion thresholds using energy-ledger margins, runner-up separation, and perturbation stability.

## Inputs

- Energy ledger entries.
- Decision ledger entries.
- Promotion outcomes.
- Review labels where available.

## Outputs

- Margin distribution report.
- Flip-rate report.
- Threshold calibration report.
- Policy impact diff.
- Calibration receipt.

## Gates

- At least 30 examples for statistical claims.
- Enumerate all examples when count is 10 or fewer.
- Low-margin bucket report required.
- Flip-rate threshold policy present.
- Policy impact diff required before threshold changes.

## Boundaries

- No threshold change without policy diff.
- No canonical promotion for low-margin unstable evidence.
- No aggregate statistical claim below sample-size gate.
