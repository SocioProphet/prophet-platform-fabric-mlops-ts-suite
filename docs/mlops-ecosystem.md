# Prophet MLOps Ecosystem (beyond Ray)

Ray (Train + Serve) is a **great default distributed runtime**, but Prophet should not assume
the world ends at Ray.

Finance teams vary wildly in what they trust and what they already run:
- some want KServe-style “standard” InferenceService CRDs,
- some want high-performance GPU inference (e.g., Triton),
- some standardize on Spark for feature engineering,
- some already have MLflow + Feast everywhere,
- some want Kubeflow-style training CRDs for PyTorch/MPI jobs.

So the Prophet stance is:

> **Prophet defines the contracts. The ecosystem provides the engines.**

Prophet ships a curated, open-source **reference stack**, and supports additional engines
through adapters.

---

## The contracts Prophet should own

### 1) Workflow contract (pipelines)
**Goal:** turn “train/eval/promote/deploy” into a reproducible, auditable workflow.

**Default engine:** Argo Workflows (K8s CRD workflows)  
**Alternatives:** Tekton, Airflow, Prefect, etc. (integrations)

### 2) Training runtime contract (distributed execution)
**Goal:** run training jobs on CPU/GPU, scale out, checkpoint reliably.

**Default engine:** Ray Train via KubeRay RayJob  
**Alternatives:**
- Kubeflow Trainer / Training Operator CRDs (PyTorchJob, MPIJob, …)
- Spark Operator (for feature engineering / batch ML pipelines)
- Plain Kubernetes Jobs (simple baselines)

### 3) Serving runtime contract (production inference)
**Goal:** serve models with policy, canaries, rollbacks, and observability.

**Default engine:** Ray Serve via KubeRay RayService  
**Alternatives:**
- KServe (InferenceService CRDs)
- Seldon Core 2 (MLOps/LLMOps framework)
- Triton (high-performance inference server; usually deployed per-model)

### 4) Registry & provenance contract (reproducibility)
**Goal:** every model has provenance:
- dataset version
- code version / container digest
- hyperparams
- metrics + evaluation report
- approvals and promotion history

**Default engine:** MLflow (OSS) + object storage for artifacts  
**Alternatives:** Prophet-native registry service, or other registries.

### 5) Feature store contract (training/serving consistency)
**Goal:** guarantee the same features show up online and offline.

**Default engine:** Feast (OSS; operator-managed recommended)  
**Alternatives:** custom features in Prophet lake + materializers, or other stores.

### 6) Observability contract (traces + metrics)
**Goal:** make training/serving debuggable and safe:
- metrics (Prometheus)
- logs (Loki)
- traces (OpenTelemetry)

**Default engine:** OpenTelemetry Operator + collector CRs  
**Alternatives:** vendor tools / other collectors.

### 7) Accelerator contract (GPUs)
**Goal:** make GPUs boring:
- drivers
- device plugin
- runtime/toolkit
- monitoring hooks

**Default engine:** NVIDIA GPU Operator (where applicable)

---

## Where this fits in the Prophet Hierarchy Tree (PHT)

Fabric → Data plane → Prophet platform services → **Prophet ML plane** → SocioProfit app

The ML plane is a *platform subsystem*, not an app subsystem.

---

## What we ship in this repo

This repo now includes **optional Helmfiles** for MLOps ecosystem add-ons:

- `helm/helmfile-mlops-core.yaml`
  - Argo Workflows
  - MLflow
  - Feast Operator
  - Spark Operator
  - OpenTelemetry Operator

- `helm/helmfile-ml-serving.yaml`
  - KServe (OCI charts)
  - Seldon Core 2 (CRDs + operator)

- `helm/helmfile-gpu.yaml`
  - NVIDIA GPU Operator

Ray remains installed via the main `helm/helmfile.yaml` (KubeRay + Prophet Ray atoms).

---

## Recommended default posture (sane and minimal)

**Core cluster (GPU capable):**
- Ray (Train + Serve)
- Argo Workflows (pipelines)
- MLflow (tracking/registry)
- OpenTelemetry (traces)
- GPU operator (if you manage drivers/toolkit in-cluster)

**Edge cluster:**
- Ray Serve only (small)
- no training by default
- traces/metrics minimal but present

---

## The non-negotiable rule

Databases and serving engines are replaceable.

**Durability is not.**

Truth lives in:
- commit log (ordered, replayable)
- immutable lake (manifests + segments)

Everything else can be rebuilt.



---

## Time-series model families

For the Prophet-supported time-series model taxonomy and rollout tiers, see `docs/time-series-model-families.md`.


---

## Time-Series Suite

See `docs/time-series-suite-v1.md` and `docs/time-series-model-families.md` for the model packs Prophet ships and how they are evaluated/promoted.
