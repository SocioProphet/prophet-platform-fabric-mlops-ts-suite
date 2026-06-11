# Assessment HITL Evaluation Pack v0.1

Status: draft pack skeleton

## Purpose

Evaluates high-stakes assessment models, including interview, personality, leadership, and human-behavior inference workflows, under human-in-the-loop gates.

## Inputs

- Model assessment outputs.
- Prompt/version metadata where LLMs are used.
- Expert rubric references.
- Review labels.
- Fairness slices where available.

## Outputs

- Human-in-the-loop review manifest.
- Fairness evaluation report.
- Prompt/version receipt.
- Score calibration report.
- Assessment governance receipt.

## Gates

- Human review required.
- Prompt and model version pinned.
- Rubric provenance required.
- Fairness evaluation required when demographic or protected-class slices are available.
- No automated high-stakes decision without review.
- TritFabric promotion gate required before registry promotion.

## TritFabric alignment

This pack is designed to hand off artifacts through TritFabric Atlas registry and promotion discipline:

- `RegistryService.ListArtifacts` for assessment outputs.
- `RegistryService.GetLedger` for run ledger retrieval.
- `RegistryService.PromoteArtifact` only after HITL and policy gates pass.
- `OrchestratorService.SubmitTrainJob` or `SubmitTuneStudy` for governed training/evaluation jobs.

## Boundaries

- No direct employment, credit, insurance, legal, or similarly high-impact automated decisioning.
- No production promotion without human review receipt.
- No demographic fairness claim without adequate sample size and documented slices.
