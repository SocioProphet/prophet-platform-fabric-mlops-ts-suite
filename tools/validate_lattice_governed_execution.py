#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "lattice_data_governai_execution_0001.json"
RAY_RUNTIME_REF = "runtime-asset:prophet-ray-ml:0.1.0"
BEAM_RUNTIME_REF = "runtime-asset:prophet-beam-dataops:0.1.0"

REQUIRED_TOP_LEVEL = {
    "apiVersion",
    "kind",
    "fixtureId",
    "dataProductRef",
    "dataContractRef",
    "runtimeAssetRef",
    "runtimeRefs",
    "policyRef",
    "rayJob",
    "beamPipeline",
    "lineageRuns",
    "evaluationBundle",
    "promotionGate",
    "platformAssetRecords",
    "safety",
}


def fail(message: str) -> None:
    print(f"ERR: {message}", file=sys.stderr)
    raise SystemExit(2)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    require(isinstance(value, str) and bool(value), f"{key} must be a non-empty string")
    return value


def require_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    require(isinstance(value, list), f"{key} must be a list")
    return value


def validate_job(job: dict[str, Any], *, kind: str, engine: str, runtime_ref: str, data_product_ref: str) -> None:
    require(job.get("kind") == kind, f"{kind}: kind mismatch")
    require(job.get("engine") == engine, f"{kind}: engine mismatch")
    require(job.get("runtimeEnvRef") == runtime_ref, f"{kind}: runtimeEnvRef must match role-specific RuntimeAsset")
    require(data_product_ref in require_list(job, "inputRefs"), f"{kind}: inputRefs must include DataProduct")
    require_string(job, "lineageRunRef")
    require(job.get("executionMode") == "dry-run", f"{kind}: executionMode must be dry-run")
    require(job.get("network") == "none", f"{kind}: network must be none for fixture proof")
    require(job.get("secrets") == "none", f"{kind}: secrets must be none for fixture proof")


def validate_platform_record(record: dict[str, Any]) -> None:
    require(record.get("kind") == "PlatformAssetRecord", "platform record kind must be PlatformAssetRecord")
    require_string(record, "assetId")
    asset_kind = require_string(record, "assetKind")
    require_string(record, "producerRepo")
    require(record.get("producerRepo") == "SocioProphet/prophet-platform-fabric-mlops-ts-suite", "producerRepo mismatch")
    surfaces = require_list(record, "compatibilitySurfaces")
    require(bool(surfaces), "compatibilitySurfaces must not be empty")
    if asset_kind == "ray-job-dry-run":
        require(record.get("runtimeRef") == RAY_RUNTIME_REF, "Ray platform record runtimeRef mismatch")
    if asset_kind == "beam-pipeline-dry-run":
        require(record.get("runtimeRef") == BEAM_RUNTIME_REF, "Beam platform record runtimeRef mismatch")


def validate_fixture(data: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    require(not missing, f"missing top-level keys: {', '.join(missing)}")
    require(data["apiVersion"] == "mlops.socioprophet.dev/v1", "apiVersion mismatch")
    require(data["kind"] == "LatticeGovernedExecutionFixture", "kind mismatch")

    data_product_ref = require_string(data, "dataProductRef")
    data_contract_ref = require_string(data, "dataContractRef")
    runtime_ref = require_string(data, "runtimeAssetRef")
    policy_ref = require_string(data, "policyRef")
    require(data_product_ref.startswith("urn:srcos:data-product:"), "dataProductRef must be SourceOS DataProduct URN")
    require(data_contract_ref.startswith("urn:srcos:data-contract:"), "dataContractRef must be SourceOS DataContract URN")
    require(runtime_ref == RAY_RUNTIME_REF, "top-level runtimeAssetRef must be Ray runtime for model evaluation")
    require(policy_ref.startswith("urn:srcos:policy:"), "policyRef must be SourceOS policy URN")
    runtime_refs = data.get("runtimeRefs")
    require(isinstance(runtime_refs, dict), "runtimeRefs must be object")
    require(runtime_refs.get("rayRuntimeRef") == RAY_RUNTIME_REF, "runtimeRefs.rayRuntimeRef mismatch")
    require(runtime_refs.get("beamRuntimeRef") == BEAM_RUNTIME_REF, "runtimeRefs.beamRuntimeRef mismatch")

    ray_job = data["rayJob"]
    beam_pipeline = data["beamPipeline"]
    require(isinstance(ray_job, dict), "rayJob must be object")
    require(isinstance(beam_pipeline, dict), "beamPipeline must be object")
    validate_job(ray_job, kind="RayJobDryRunPlan", engine="ray-train", runtime_ref=RAY_RUNTIME_REF, data_product_ref=data_product_ref)
    validate_job(beam_pipeline, kind="BeamPipelineDryRunPlan", engine="apache-beam", runtime_ref=BEAM_RUNTIME_REF, data_product_ref=data_product_ref)

    lineage_runs = require_list(data, "lineageRuns")
    require(len(lineage_runs) == 2, "lineageRuns must include Ray and Beam runs")
    lineage_by_id = {require_string(run, "id"): run for run in lineage_runs if isinstance(run, dict)}
    require(ray_job["lineageRunRef"] in lineage_by_id, "Ray lineageRunRef missing from lineageRuns")
    require(beam_pipeline["lineageRunRef"] in lineage_by_id, "Beam lineageRunRef missing from lineageRuns")
    require(lineage_by_id[ray_job["lineageRunRef"]].get("runtimeRef") == RAY_RUNTIME_REF, "Ray lineage runtimeRef mismatch")
    require(lineage_by_id[beam_pipeline["lineageRunRef"]].get("runtimeRef") == BEAM_RUNTIME_REF, "Beam lineage runtimeRef mismatch")

    evaluation = data["evaluationBundle"]
    require(isinstance(evaluation, dict), "evaluationBundle must be object")
    require(evaluation.get("runtimeRef") == RAY_RUNTIME_REF, "evaluationBundle.runtimeRef must be Ray runtime")
    supporting = require_list(evaluation, "supportingRuntimeRefs")
    require(BEAM_RUNTIME_REF in supporting, "evaluationBundle.supportingRuntimeRefs must include Beam runtime")
    require(data_product_ref in require_list(evaluation, "inputRefs"), "evaluationBundle.inputRefs must include DataProduct")
    require(evaluation.get("verdict") in {"approved", "rejected", "needs-review", "blocked", "informational"}, "invalid evaluation verdict")

    gate = data["promotionGate"]
    require(isinstance(gate, dict), "promotionGate must be object")
    require(gate.get("state") in {"approved", "rejected", "needs-review", "blocked", "informational"}, "invalid promotion gate state")
    requirements = require_list(gate, "requires")
    require(any("Ray RuntimeAsset" in item for item in requirements), "promotionGate must require Ray RuntimeAsset evidence")
    require(any("Beam RuntimeAsset" in item for item in requirements), "promotionGate must require Beam RuntimeAsset evidence")

    records = require_list(data, "platformAssetRecords")
    require(len(records) >= 2, "platformAssetRecords must include Ray and Beam records")
    for record in records:
        require(isinstance(record, dict), "platformAssetRecords entries must be objects")
        validate_platform_record(record)

    safety = data["safety"]
    require(isinstance(safety, dict), "safety must be object")
    require(safety.get("hostMutation") is False, "safety.hostMutation must be false")
    require(safety.get("network") == "none", "safety.network must be none")
    require(safety.get("secrets") == "none", "safety.secrets must be none")
    require(safety.get("mode") == "fixture-only", "safety.mode must be fixture-only")


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("fixture must be a JSON object")
    validate_fixture(data)
    print(json.dumps({"ok": True, "validated": str(FIXTURE)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
