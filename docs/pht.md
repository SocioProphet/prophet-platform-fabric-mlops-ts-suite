# Prophet Hierarchy Tree (PHT)

This is the canonical “what sits on what” model.

**Prophet Platform** is the platform.
**SocioProfit** is an application served over Prophet platform services.

The **data mesh fabric** is the substrate underneath Prophet.

---

## PHT-0: Global Infrastructure
- compute, network, storage in each region/edge location
- IAM / KMS / DNS (or equivalents)

## PHT-1: Kubernetes Fleet (multi-cluster)
- one cluster per region (and per edge site)
- each cluster has:
  - node pools (edge vs core)
  - storage classes
  - ingress/egress
  - fleet registration (Prophet)

## PHT-2: Fabric Baseline (multi-mesh / standard runtime)
These are “always on” in every cluster:

- cert-manager
- external-secrets
- service mesh (Istio) + gateways
- observability (metrics + logs)
- GitOps (Argo CD)
- policy guardrails (optional: Kyverno / Gatekeeper)
- chaos testing (non-prod default)

This layer turns Kubernetes into a consistent, operable substrate.

## PHT-3: Prophet Data Plane (durability & primitives)
Prophet owns durability. Databases are query engines, not truth.

**Authoritative truth:**
- commit log (Kafka in dev; pluggable in principle)
- immutable lake / object store (Parquet/Arrow segments + manifests)

**Supporting primitives:**
- Postgres (metadata/control-plane)
- Redis / Memcached (caching)
- Blazegraph (semantic/constraint store)

## PHT-4: Prophet Platform Services (1st-party pods)
These are the “platform atoms” we ship as Prophet:

- `prophet-control-plane` (tenants, authZ, placement, failover control)
- `prophet-ingest-gateway` (event IDs, validation, ingest)
- `prophet-lake-writer` (segments + manifests)
- `prophet-materializer-*` (hydrate engines from truth)
- `prophet-query-gateway` (one query surface, routing + policy)
- `prophet-reasoner` (neuro-symbolic reasoning services)
- `prophet-agent` (daemonset for fleet/edge operations)

## PHT-5: Query Engines (replaceable materialized views)
These are “platform-managed engines” behind Prophet contracts:

- QuestDB (hot time-series)
- ClickHouse (heavy analytics)
- ArcticDB gateway (dataset/version artifacts)
- Blazegraph (graph querying) if used directly in reasoning
- Postgres (metadata)

## PHT-6: SocioProfit App (served over Prophet)
SocioProfit is a consumer of Prophet services, not a substrate.

Typical app atoms:
- `socioprofit-web` (UI)
- `socioprofit-api` (business API)
- `socioprofit-worker` (async jobs, reports, pipelines)

**Rule:** SocioProfit talks to Prophet via Prophet APIs (ingest/query/reasoning).
Direct database access is strongly discouraged (breaks portability and policy).

---

## Why this layering matters

- Prophet can be sold as a platform product (HA/DR, durability, reasoning, data services).
- SocioProfit can be shipped as an app SKU (or a flagship app) that proves the platform.
- The fabric stays boring and standardized across clusters and customers.


---

## Time-series suite

Time-series model families, specs, and workflow templates are part of the Prophet ML plane.
See `docs/time-series-suite-v1.md`.
