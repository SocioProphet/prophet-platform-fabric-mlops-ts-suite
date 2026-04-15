# Composable Atoms Catalog (Prophet Platform + SocioProfit App)

In Prophet, an **atom** is the smallest independently deployable “platform unit” with a stable contract:
- one Helm chart (or operator + CR)
- explicit inputs/outputs
- health/readiness probes
- Prometheus metrics
- logs
- upgrade/rollback plan
- backup/restore plan (if stateful)
- a clear place in the HA/DR story

The goal: ship a **platform (Prophet)** plus a **flagship app (SocioProfit)** that can be deployed consistently across:
- edge clusters
- regional core clusters
- DR clusters

---

## 1) Fabric atoms (baseline every cluster)

### 1.1 cert-manager (3rd-party)
**Why:** cluster-wide certificate issuance (mesh, ingress, internal TLS)

**K8s type:** Deployments + CRDs  
**Namespace:** `cert-manager`

### 1.2 External Secrets Operator (3rd-party)
**Why:** sync secrets from your secrets backend (Vault / cloud secret manager / etc.)

**K8s type:** Deployments + CRDs  
**Namespace:** `external-secrets`

### 1.3 Service mesh (Istio) (3rd-party)
**Why:** mTLS, traffic policy, telemetry, cross-cluster routing

**K8s type:** Deployments + CRDs + Gateways  
**Namespaces:** `istio-system`, `istio-ingress`

> Mesh policy: apps are injected by default; stateful DBs start non-injected until proven safe.

### 1.4 Observability (3rd-party)
**Why:** finance-grade operations without guessing

**Components:**
- kube-prometheus-stack (Prometheus + Alertmanager + Grafana)
- Loki (logs)

**Namespace:** `observability`

### 1.5 Chaos testing (3rd-party, non-prod default)
**Why:** HA/DR claims must be tested, not promised.

**Component:** Chaos Mesh  
**Namespace:** `chaos-mesh`

### 1.6 GitOps (3rd-party)
**Why:** stable, repeatable multi-cluster rollouts

**Component:** Argo CD  
**Namespace:** `argocd`

---

## 2) Data plane atoms (core clusters; subset on edge)

### 2.1 Object store (S3-compatible)
**Dev default:** MinIO  
**Prod:** S3 / Ceph / whatever your infra standard is

**Purpose:**
- immutable lake segments (Parquet/Arrow)
- backups
- ArcticDB backing store (when used)

**Namespace:** `data`
### 2.2 Commit log (platform durability plane)
**Dev default:** Kafka (Bitnami chart)  
**Alternatives:** Pulsar, NATS JetStream, etc. (behind the same platform ingestion contract)

**Purpose:**
- authoritative ordering for events (idempotent, replayable)
- regional HA via replication across AZs
- cross-region DR via async replication (MirrorMaker2 or equivalent)

**Namespace:** `data`



### 2.2 Postgres HA (metadata/control-plane store)
**Operator:** CloudNativePG (CNPG)

**Purpose:**
- tenant metadata
- authZ policy storage
- job state (if needed)
- platform configuration

**Namespace:** `data` (operator in `cnpg-system`)

### 2.3 Redis
**Purpose:** caching, rate limits, ephemeral queues  
**Not a source of truth.**

**Namespace:** `data`

### 2.4 Memcached
**Purpose:** ephemeral cache, edge-friendly  
**Namespace:** `data`

### 2.5 Blazegraph (RDF/SPARQL)
**Purpose:** semantic graph store (domain constraints, ontologies, explanations)  
**Namespace:** `data`

---

## 3) Time-series / analytics atoms

### 3.1 QuestDB (hot time-series)
**Purpose:** hot ingest + short retention + edge-local queries  
**Namespace:** `data`  
**Note:** OSS does not provide native replication/failover; platform owns HA/DR.

### 3.2 ClickHouse (heavy analytics)
**Purpose:** long retention, big scans, joins, multi-tenant analytics serving  
**Namespace:** `data`  
**Deployment:** Altinity operator + ClickHouseInstallation (CHI)

### 3.3 ArcticDB gateway (embedded dataset/version store)
**Purpose:** versioned DataFrame artifacts for model training/backtesting  
**Namespace:** `data`  
**Deployment:** gateway Deployment wrapping embedded ArcticDB

> Licensing note: if you require strict OSS-only, pin to Apache-converted versions.

---

## 4) Prophet platform atoms (1st-party pods)

These are the pods we ship as **Prophet Platform**.

### 4.1 prophet-control-plane (API)
**Purpose:**
- tenants, authN/authZ
- placement (which cluster/region)
- policy
- routing/failover control (fencing tokens, epochs)

**K8s type:** Deployment + Service  
**Namespace:** `prophet-system`

### 4.2 prophet-ingest-gateway
**Purpose:** ingest events from customers/apps (ticks, features, graph events)

**Responsibilities:**
- idempotency keys / event IDs
- validation + schema enforcement
- push into the platform commit log and/or lake writer

**K8s type:** Deployment + Service  
**Namespace:** `prophet-system`

### 4.3 prophet-lake-writer
**Purpose:** converts event streams into immutable Parquet/Arrow segments + manifests

**K8s type:** Deployment (or Jobs/CronJobs)  
**Namespace:** `prophet-system`

### 4.4 prophet-materializer-questdb
**Purpose:** tail the platform log/segments and materialize hot windows into QuestDB  
**Namespace:** `prophet-system`

### 4.5 prophet-materializer-clickhouse
**Purpose:** tail the platform log/segments and materialize into ClickHouse  
**Namespace:** `prophet-system`

### 4.6 prophet-query-gateway
**Purpose:** single query surface across stores (hot vs cold routing)  
**Namespace:** `prophet-system`

### 4.7 prophet-reasoner
**Purpose:** neuro-symbolic + constraint-driven subgraph reasoning (your IP)  
**Namespace:** `prophet-system`

### 4.8 prophet-agent (DaemonSet)
**Purpose:** node/cluster agent:
- health, inventory, metrics scraping helpers
- edge→core syncing helpers
- secure bootstrap + registration

**K8s type:** DaemonSet  
**Namespace:** `prophet-system`

---

## 5) Naming conventions (recommended)

- Namespaces:
  - `prophet-system` (SocioProfit 1st-party pods)
  - `data` (databases/caches)
  - `observability`, `istio-system`, `istio-ingress`, `cert-manager`, `external-secrets`, `argocd`

- Labels:
  - `app.kubernetes.io/name`
  - `app.kubernetes.io/part-of: prophet-platform`
  - `socioprofit.com/atom: <atom-name>`
  - `socioprofit.com/tier: fabric|data|platform`

This makes multi-cluster fleet automation vastly easier.


## 6) SocioProfit app atoms (1st-party app pods)

SocioProfit is an application that runs **on top of** Prophet platform services.

### 6.1 socioprofit-api
**Purpose:** business API for the SocioProfit app (tenants, UI flows, reporting)

### 6.2 socioprofit-web
**Purpose:** web UI for SocioProfit

### 6.3 socioprofit-worker
**Purpose:** asynchronous jobs (reports, exports, scheduled computations)

**Rule:** SocioProfit should use Prophet APIs (query/ingest/reasoning) rather than direct DB access.


## 7) Ray ML atoms (Prophet ML plane)

### 7.1 kuberay-operator
**Purpose:** Kubernetes-native management of Ray clusters/jobs/serve apps  
**Namespace:** `kuberay-system`

### 7.2 prophet-ray-serve (RayService)
**Purpose:** managed Ray Serve application as a K8s resource  
**Namespace:** `prophet-ml`

### 7.3 prophet-ray-train (RayJob)
**Purpose:** managed Ray Train workload (ephemeral cluster + job submission)  
**Namespace:** `prophet-ml`

See `docs/mlops-ray.md`.


## 8) MLOps ecosystem atoms (optional add-ons)

These are ecosystem components that Prophet can integrate with. Prophet owns the contracts;
these provide engines.

### 8.1 argo-workflows
**Purpose:** workflow/pipeline orchestration as K8s CRDs  
**Namespace:** `prophet-workflows`

### 8.2 mlflow
**Purpose:** experiment tracking + (optional) model registry  
**Namespace:** `prophet-mlops`

### 8.3 feast-operator
**Purpose:** manage Feast feature stores on Kubernetes  
**Namespace:** `prophet-mlops`

### 8.4 spark-operator
**Purpose:** run Spark applications as CRDs for large-scale feature engineering  
**Namespace:** `spark-operator`

### 8.5 opentelemetry-operator
**Purpose:** manage OpenTelemetry collectors + auto-instrumentation  
**Namespace:** `observability`

### 8.6 kserve (optional)
**Purpose:** standardized model serving CRDs (InferenceService)  
**Namespace:** `kserve`

### 8.7 seldon-core-v2 (optional)
**Purpose:** alternative MLOps/LLMOps serving framework  
**Namespace:** `seldon-mesh`

### 8.8 gpu-operator (optional)
**Purpose:** manage NVIDIA GPU software stack on Kubernetes  
**Namespace:** `gpu-operator`

See `docs/mlops-ecosystem.md`.


---

## Time-series models

Model families supported by Prophet are documented in `docs/time-series-model-families.md`.


---

## Time-series suite delivery atoms

### prophet-ts-workflows
**Purpose:** installs reference Argo WorkflowTemplates for time-series training and example model specs (ConfigMaps).  
**Namespace:** `prophet-workflows`

This is the “glue” that turns the time-series model family taxonomy into an executable pipeline.

### prophet-model images (reference)
These are shipped as Dockerfiles/templates under `docker/`:
- `prophet-models-classical`
- `prophet-models-garch`
- `prophet-models-deep`
- `prophet-models-surfaces`

They are used by RayJobs / K8s Jobs, not deployed as long-running services.
