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
REPLAY_BUNDLE_REF = "urn:srcos:evidence-bundle:lattice-governed-execution-0001"

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
    "expectedArtifacts",
    "metricExpectations",
    "lineageRuns",
    "lineageReceipts",
    "replayEvidenceBundle",
    "evaluationBundle",
    "promotionGate",
    "platformAssetRecords",
    "safety",
}
REQUIRED_ARTIFACT_KINDS = {"metrics", "quality-profile", "model-candidate"}
REQUIRED_RAY_METRICS = {"factuality_f1", "grounding_precision", "training_records"}
REQUIRED_BEAM_METRICS = {"quality_completeness", "annotation_coverage", "duplicate_rate"}


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


def validate_expected_artifacts(data: dict[str, Any]) -> set[str]:
    artifacts = require_list(data, "expectedArtifacts")
    artifact_kinds = set()
    artifact_refs = set()
    for artifact in artifacts:
        require(isinstance(artifact, dict), "expectedArtifacts entries must be objects")
        artifact_ref = require_string(artifact, "artifactRef")
        artifact_refs.add(artifact_ref)
        artifact_kind = require_string(artifact, "artifactKind")
        artifact_kinds.add(artifact_kind)
        require(artifact_kind in REQUIRED_ARTIFACT_KINDS, f"unexpected artifactKind {artifact_kind}")
        require_string(artifact, "producerRef")
        runtime_ref = require_string(artifact, "runtimeRef")
        if artifact_kind in {"metrics", "model-candidate"}:
            require(runtime_ref == RAY_RUNTIME_REF, f"{artifact_kind} must use Ray runtime")
        if artifact_kind == "quality-profile":
            require(runtime_ref == BEAM_RUNTIME_REF, "quality-profile must use Beam runtime")
        require_string(artifact, "mediaType")
        require_string(artifact, "evidenceRef")
        require(artifact.get("required") is True, "expected artifact must be required")
    missing = REQUIRED_ARTIFACT_KINDS - artifact_kinds
    require(not missing, f"missing expected artifact kinds: {missing}")
    return artifact_refs


def validate_metric_expectations(data: dict[str, Any]) -> None:
    metrics = data.get("metricExpectations")
    require(isinstance(metrics, dict), "metricExpectations must be object")
    ray = metrics.get("ray")
    beam = metrics.get("beam")
    require(isinstance(ray, dict), "metricExpectations.ray must be object")
    require(isinstance(beam, dict), "metricExpectations.beam must be object")
    require(ray.get("runtimeRef") == RAY_RUNTIME_REF, "Ray metric runtime mismatch")
    require(beam.get("runtimeRef") == BEAM_RUNTIME_REF, "Beam metric runtime mismatch")
    ray_metrics = {metric.get("name"): metric for metric in require_list(ray, "requiredMetrics") if isinstance(metric, dict)}
    beam_metrics = {metric.get("name"): metric for metric in require_list(beam, "requiredMetrics") if isinstance(metric, dict)}
    require(REQUIRED_RAY_METRICS <= set(ray_metrics), f"missing Ray metrics: {REQUIRED_RAY_METRICS - set(ray_metrics)}")
    require(REQUIRED_BEAM_METRICS <= set(beam_metrics), f"missing Beam metrics: {REQUIRED_BEAM_METRICS - set(beam_metrics)}")
    for metric in list(ray_metrics.values()) + list(beam_metrics.values()):
        require("actual" in metric, "metric must include actual")
        require(metric.get("status") in {"pass", "warn", "fail"}, "metric status invalid")
        if "min" in metric:
            require(metric["actual"] >= 0, "metric actual must be non-negative")
        if "max" in metric:
            require(metric["actual"] >= 0, "metric actual must be non-negative")
    require(ray_metrics["factuality_f1"]["status"] == "pass", "factuality_f1 must pass")
    require(ray_metrics["grounding_precision"]["status"] == "warn", "grounding_precision should remain warn")
    require(beam_metrics["quality_completeness"]["status"] == "pass", "quality_completeness must pass")


def validate_lineage(data: dict[str, Any], ray_job: dict[str, Any], beam_pipeline: dict[str, Any]) -> set[str]:
    lineage_runs = require_list(data, "lineageRuns")
    require(len(lineage_runs) == 2, "lineageRuns must include Ray and Beam runs")
    lineage_by_id = {require_string(run, "id"): run for run in lineage_runs if isinstance(run, dict)}
    require(ray_job["lineageRunRef"] in lineage_by_id, "Ray lineageRunRef missing from lineageRuns")
    require(beam_pipeline["lineageRunRef"] in lineage_by_id, "Beam lineageRunRef missing from lineageRuns")
    require(lineage_by_id[ray_job["lineageRunRef"]].get("runtimeRef") == RAY_RUNTIME_REF, "Ray lineage runtimeRef mismatch")
    require(lineage_by_id[beam_pipeline["lineageRunRef"]].get("runtimeRef") == BEAM_RUNTIME_REF, "Beam lineage runtimeRef mismatch")

    receipts = require_list(data, "lineageReceipts")
    require(len(receipts) == 2, "lineageReceipts must include Ray and Beam receipts")
    receipt_refs = set()
    for receipt in receipts:
        require(isinstance(receipt, dict), "lineageReceipts entries must be objects")
        receipt_id = require_string(receipt, "receiptId")
        receipt_refs.add(receipt_id)
        lineage_ref = require_string(receipt, "lineageRunRef")
        require(lineage_ref in lineage_by_id, "receipt lineageRunRef must point to lineageRuns")
        require_string(receipt, "jobRef")
        runtime_ref = require_string(receipt, "runtimeRef")
        if "ray" in receipt_id:
            require(runtime_ref == RAY_RUNTIME_REF, "Ray receipt runtime mismatch")
        if "beam" in receipt_id:
            require(runtime_ref == BEAM_RUNTIME_REF, "Beam receipt runtime mismatch")
        require_list(receipt, "inputDigestRefs")
        require_list(receipt, "outputDigestRefs")
        require_string(receipt, "evidenceRef")
        require(receipt.get("replayable") is True, "lineage receipt must be replayable")
    return receipt_refs


def validate_replay_bundle(data: dict[str, Any], artifact_refs: set[str], receipt_refs: set[str]) -> None:
    bundle = data.get("replayEvidenceBundle")
    require(isinstance(bundle, dict), "replayEvidenceBundle must be object")
    require(bundle.get("bundleId") == REPLAY_BUNDLE_REF, "replay bundle id mismatch")
    require(bundle.get("kind") == "ReplayEvidenceBundle", "replay bundle kind mismatch")
    require(bundle.get("mode") == "dry-run", "replay bundle mode must be dry-run")
    require(set(require_list(bundle, "runtimeRefs")) == {RAY_RUNTIME_REF, BEAM_RUNTIME_REF}, "replay runtimeRefs mismatch")
    require(set(require_list(bundle, "artifactRefs")) == artifact_refs, "replay artifactRefs must match expectedArtifacts")
    require(set(require_list(bundle, "lineageReceiptRefs")) == receipt_refs, "replay lineageReceiptRefs must match receipts")
    commands = require_list(bundle, "replayCommandRefs")
    require("/lattice mlops ray run community_truth_demo --runtime prophet-ray-ml --dry-run" in commands, "replay bundle missing Ray command")
    require("/lattice dataops beam run community_truth_demo --runtime prophet-beam-dataops --dry-run" in commands, "replay bundle missing Beam command")
    require(bundle.get("network") == "none", "replay bundle network must be none")
    require(bundle.get("secrets") == "none", "replay bundle secrets must be none")
    require(bundle.get("hostMutation") is False, "replay bundle hostMutation must be false")


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
    if asset_kind == "replay-evidence-bundle":
        require(record.get("assetId") == REPLAY_BUNDLE_REF, "Replay bundle PlatformAssetRecord assetId mismatch")
        require("agentplane" in surfaces, "Replay bundle must surface to AgentPlane")
        require("sherlock-search" in surfaces, "Replay bundle must surface to Sherlock")


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

    artifact_refs = validate_expected_artifacts(data)
    validate_metric_expectations(data)
    receipt_refs = validate_lineage(data, ray_job, beam_pipeline)
    validate_replay_bundle(data, artifact_refs, receipt_refs)

    evaluation = data["evaluationBundle"]
    require(isinstance(evaluation, dict), "evaluationBundle must be object")
    require(evaluation.get("runtimeRef") == RAY_RUNTIME_REF, "evaluationBundle.runtimeRef must be Ray runtime")
    supporting = require_list(evaluation, "supportingRuntimeRefs")
    require(BEAM_RUNTIME_REF in supporting, "evaluationBundle.supportingRuntimeRefs must include Beam runtime")
    require(data_product_ref in require_list(evaluation, "inputRefs"), "evaluationBundle.inputRefs must include DataProduct")
    require(evaluation.get("verdict") in {"approved", "rejected", "needs-review", "blocked", "informational"}, "invalid evaluation verdict")
    require(evaluation.get("replayEvidenceBundleRef") == REPLAY_BUNDLE_REF, "evaluationBundle must link replayEvidenceBundle")
    eval_metric_names = {metric.get("name") for metric in require_list(evaluation, "metrics") if isinstance(metric, dict)}
    require({"factuality_f1", "grounding_precision", "quality_completeness", "annotation_coverage"} <= eval_metric_names, "evaluationBundle missing required metrics")

    gate = data["promotionGate"]
    require(isinstance(gate, dict), "promotionGate must be object")
    require(gate.get("state") in {"approved", "rejected", "needs-review", "blocked", "informational"}, "invalid promotion gate state")
    requirements = require_list(gate, "requires")
    for expected in ["Ray RuntimeAsset", "Beam RuntimeAsset", "Ray metrics artifact", "Beam quality artifact", "Ray lineage receipt", "Beam lineage receipt", "ReplayEvidenceBundle"]:
        require(any(expected in item for item in requirements), f"promotionGate must require {expected}")

    records = require_list(data, "platformAssetRecords")
    require(len(records) >= 3, "platformAssetRecords must include Ray, Beam, and replay bundle records")
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
