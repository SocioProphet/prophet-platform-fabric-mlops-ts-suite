# Atlas README Preservation v0.1

This note preserves durable model-training and orchestration vocabulary extracted from the thin Atlas bundle repositories before any future archive or retirement decision.

Source repositories:

- `SocioProphet/atlas_master_bundle_complete`

The Atlas repositories are not promoted to canonical implementation authority by this note. The purpose is to preserve concepts that belong in the Fabric/MLOps lane before Atlas can be safely retired or retained only as historical reference.

## Preserved Fabric/MLOps concepts

### 1. Prewired model study vocabulary

Atlas names prewired study scripts for model families and workloads such as GPT chat, YOLO, StyleGAN, Tacotron2, RGCN, and SRCNN.

Canonical disposition:

- Fabric/MLOps owns downstream training/evaluation pack vocabulary.
- Labs may consume these study concepts as execution surfaces.
- Model Governance Ledger remains the authority for lifecycle, promotion, consent, revocation, and governance evidence.
- Model Router remains the runtime routing authority after a model is available for selection.

### 2. Beam / Airflow / Avro orchestration vocabulary

Atlas orchestration material names Beam, Airflow, Avro schema-registry expectations, and Kafka-style event topics such as `atlas.rewire.intent`, `atlas.tune.started`, and `atlas.tune.result`.

Canonical disposition:

- Fabric/MLOps preserves training-workflow orchestration vocabulary.
- TritFabric preserves the recovered Atlas runtime/fabric lineage.
- AgentPlane owns execution/evidence-control surfaces where orchestration invokes agents or runtime jobs.
- Policy Fabric gates privileged execution, network, tool, or data movement side effects.

## Non-authority boundary

This document does not make Atlas bundle repositories authoritative. Atlas remains a candidate for archive or reference retention after extraction rows are discharged and direct tree confirmation is resolved.
