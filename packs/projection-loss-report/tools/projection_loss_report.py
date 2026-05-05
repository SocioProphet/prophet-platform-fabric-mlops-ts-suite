#!/usr/bin/env python3
"""Compile projection-loss reports for SHIR lowering operations.

The pack audits a SHIR assertion and a target projection manifest, then emits
semantic-serdes-compatible ProjectionLossReport and Receipt artifacts. It is
runtime-light: stdlib by default, optional jsonschema validation when a
semantic-serdes schema directory is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
CONFIG_HASH = "sha256:projection-loss-report-pack-v0.1-default"
SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "BLOCKING": 4}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(doc: Dict[str, Any]) -> str:
    return sha256_text(json.dumps(doc, sort_keys=True, separators=(",", ":")))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, doc: Dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def severity_max(items: Iterable[Dict[str, Any]]) -> str:
    max_name = "INFO"
    max_value = SEVERITY_ORDER[max_name]
    for item in items:
        value = SEVERITY_ORDER.get(item.get("severity", "INFO"), 0)
        if value > max_value:
            max_name = item.get("severity", "INFO")
            max_value = value
    return max_name


def normalize_bool(mapping: Dict[str, Any], key: str, default: bool) -> bool:
    value = mapping.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be boolean")


def loss_item(
    semantic_dimension: str,
    loss_mode: str,
    source_ref: str,
    explanation: str,
    severity: str,
    target_ref: Optional[str] = None,
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "semantic_dimension": semantic_dimension,
        "loss_mode": loss_mode,
        "source_ref": source_ref,
        "explanation": explanation,
        "severity": severity,
    }
    if target_ref:
        item["target_ref"] = target_ref
    return item


def assess_projection(source: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
    assertion_ref = source.get("assertion_id", "source.assertion")
    projection_ref = manifest.get("projection_id", "projection.unknown")
    strategy = manifest.get("relation_strategy", "binary_edges")
    target_ref = f"{projection_ref}.target"

    role_bindings = source.get("role_bindings", [])
    is_nary = isinstance(role_bindings, list) and len(role_bindings) > 2
    preservation = manifest.get("preservation", {})
    if not isinstance(preservation, dict):
        raise ValueError("projection manifest field 'preservation' must be an object")

    strict_publication = normalize_bool(manifest, "strict_publication", False)
    governance = manifest.get("governance", {})
    training_allowed = bool(governance.get("training_allowed", False))
    export_allowed = bool(governance.get("export_allowed", False))

    items: List[Dict[str, Any]] = []

    if is_nary:
        if strategy in {"relation_node", "hyperedge"}:
            items.append(loss_item("N_ARY_RELATION", "PRESERVED", assertion_ref, f"N-ary connector with {len(role_bindings)} role bindings is preserved using {strategy}.", "INFO", target_ref))
        else:
            items.append(loss_item("N_ARY_RELATION", "TRANSFORMED", assertion_ref, "N-ary connector is lowered into binary edge triplets; relation semantics remain recoverable only through the projection manifest and receipt.", "MEDIUM", target_ref))
    else:
        items.append(loss_item("N_ARY_RELATION", "PRESERVED", assertion_ref, "Source assertion is binary or unary-compatible; no n-ary relation loss detected.", "INFO", target_ref))

    if source.get("temporal_scope"):
        temporal_mode = preservation.get("temporal_scope")
        if temporal_mode == "preserved":
            items.append(loss_item("TEMPORAL_SCOPE", "PRESERVED", f"{assertion_ref}.temporal_scope", "Temporal scope is preserved in the target projection.", "INFO", target_ref))
        elif temporal_mode == "feature_metadata":
            items.append(loss_item("TEMPORAL_SCOPE", "ENCODED_INDIRECTLY", f"{assertion_ref}.temporal_scope", "Temporal scope is encoded as feature or manifest metadata instead of a first-class temporal graph object.", "LOW", target_ref))
        else:
            severity = "BLOCKING" if strict_publication else "HIGH"
            items.append(loss_item("TEMPORAL_SCOPE", "DROPPED", f"{assertion_ref}.temporal_scope", "Temporal scope is absent from the target projection.", severity, target_ref))

        observation_mode = preservation.get("observation_time")
        if observation_mode == "preserved":
            items.append(loss_item("OBSERVATION_TIME", "PRESERVED", f"{assertion_ref}.temporal_scope.observed_at", "Observation time is preserved.", "INFO", target_ref))
        elif observation_mode == "feature_metadata":
            items.append(loss_item("OBSERVATION_TIME", "ENCODED_INDIRECTLY", f"{assertion_ref}.temporal_scope.observed_at", "Observation time is encoded as metadata.", "LOW", target_ref))
        else:
            severity = "BLOCKING" if strict_publication else "HIGH"
            items.append(loss_item("OBSERVATION_TIME", "DROPPED", f"{assertion_ref}.temporal_scope.observed_at", "Observation time is absent from the target projection.", severity, target_ref))

    if source.get("evidence_anchors"):
        evidence_mode = preservation.get("evidence_anchors")
        if evidence_mode == "preserved":
            items.append(loss_item("EVIDENCE_ANCHOR", "PRESERVED", f"{assertion_ref}.evidence_anchors", "Evidence anchors are preserved in the projection manifest.", "INFO", target_ref))
        elif evidence_mode == "external_ref":
            items.append(loss_item("EVIDENCE_ANCHOR", "REQUIRES_EXTERNAL_LOOKUP", f"{assertion_ref}.evidence_anchors", "Evidence anchors are preserved by reference outside trainable tensors.", "LOW", target_ref))
        else:
            severity = "BLOCKING" if training_allowed or strict_publication else "HIGH"
            items.append(loss_item("EVIDENCE_ANCHOR", "DROPPED", f"{assertion_ref}.evidence_anchors", "Evidence anchors are missing from the target projection.", severity, target_ref))

    if source.get("policy_scope"):
        policy_mode = preservation.get("policy_scope")
        if policy_mode == "preserved":
            items.append(loss_item("POLICY_SCOPE", "PRESERVED", f"{assertion_ref}.policy_scope", "Policy scope is preserved in the target projection.", "INFO", target_ref))
        elif policy_mode == "external_ref":
            items.append(loss_item("POLICY_SCOPE", "REQUIRES_EXTERNAL_LOOKUP", f"{assertion_ref}.policy_scope", "Policy scope is preserved by reference outside trainable tensors.", "LOW", target_ref))
        else:
            severity = "BLOCKING" if training_allowed or export_allowed or strict_publication else "HIGH"
            items.append(loss_item("POLICY_SCOPE", "DROPPED", f"{assertion_ref}.policy_scope", "Policy scope is missing from the target projection.", severity, target_ref))

    if source.get("context"):
        context_mode = preservation.get("context", "external_ref")
        if context_mode == "preserved":
            items.append(loss_item("CONTEXT", "PRESERVED", f"{assertion_ref}.context", "Context is preserved as a target object.", "INFO", target_ref))
        elif context_mode == "external_ref":
            items.append(loss_item("CONTEXT", "REQUIRES_EXTERNAL_LOOKUP", f"{assertion_ref}.context", "Context is preserved by reference.", "LOW", target_ref))
        else:
            items.append(loss_item("CONTEXT", "DROPPED", f"{assertion_ref}.context", "Context is not present in the target projection.", "HIGH", target_ref))

    if source.get("governance"):
        governance_mode = preservation.get("governance", "external_ref")
        if governance_mode == "preserved":
            items.append(loss_item("CURATION_STATE", "PRESERVED", f"{assertion_ref}.governance", "Governance and curation state are preserved.", "INFO", target_ref))
        elif governance_mode == "external_ref":
            items.append(loss_item("CURATION_STATE", "REQUIRES_EXTERNAL_LOOKUP", f"{assertion_ref}.governance", "Governance and curation state are preserved by receipt reference.", "LOW", target_ref))
        else:
            items.append(loss_item("CURATION_STATE", "DROPPED", f"{assertion_ref}.governance", "Governance and curation state are absent from projection.", "HIGH", target_ref))

    if source.get("noise_assessments"):
        noise_mode = preservation.get("noise_assessment", "dropped")
        if noise_mode == "preserved":
            items.append(loss_item("NOISE_ASSESSMENT", "PRESERVED", f"{assertion_ref}.noise_assessments", "Noise assessments are preserved.", "INFO", target_ref))
        elif noise_mode == "external_ref":
            items.append(loss_item("NOISE_ASSESSMENT", "REQUIRES_EXTERNAL_LOOKUP", f"{assertion_ref}.noise_assessments", "Noise assessments are preserved by reference.", "LOW", target_ref))
        else:
            items.append(loss_item("NOISE_ASSESSMENT", "DROPPED", f"{assertion_ref}.noise_assessments", "Noise assessments are not present in the target projection.", "MEDIUM", target_ref))

    return items, any(item.get("severity") == "BLOCKING" for item in items)


def semantic_leakage_block(manifest: Dict[str, Any]) -> Dict[str, Any]:
    leakage = manifest.get("semantic_leakage", {})
    if not isinstance(leakage, dict):
        raise ValueError("projection manifest field 'semantic_leakage' must be an object when present")
    return {
        "checked": bool(leakage.get("checked", False)),
        "risk_level": leakage.get("risk_level", "UNKNOWN"),
        "markers": leakage.get("markers", ["NONE"]),
        "mitigations": leakage.get("mitigations", []),
    }


def governance_block(manifest: Dict[str, Any], blocking: bool) -> Dict[str, Any]:
    governance = manifest.get("governance", {})
    if not isinstance(governance, dict):
        raise ValueError("projection manifest field 'governance' must be an object when present")
    return {
        "review_status": "ESCALATED" if blocking else governance.get("review_status", "REQUIRED"),
        "export_allowed": bool(governance.get("export_allowed", not blocking)) and not blocking,
        "training_allowed": bool(governance.get("training_allowed", not blocking)) and not blocking,
        "policy_basis": governance.get("policy_basis", ["shir.v0.1.projection_loss_report_required"]),
    }


def build_report(source: Dict[str, Any], manifest: Dict[str, Any], source_hash: str, manifest_hash: str, timestamp: str) -> Tuple[Dict[str, Any], bool]:
    projection_ref = manifest.get("projection_id", f"projection.{manifest_hash[:12]}")
    receipt_ref = f"shir.receipt.projection_loss.{manifest_hash[:12]}"
    loss_items, blocking = assess_projection(source, manifest)
    report = {
        "report_id": f"shir.loss.{manifest_hash[:12]}",
        "kind": "ProjectionLossReport",
        "projection_ref": projection_ref,
        "source_representation": manifest.get("source_representation", "SHIR"),
        "target_representation": manifest.get("target_representation", "PYG_HETERODATA"),
        "loss_items": loss_items,
        "semantic_leakage": semantic_leakage_block(manifest),
        "governance": governance_block(manifest, blocking),
        "receipt_ref": receipt_ref,
        "replay": {
            "inputs_hash": f"sha256:{source_hash}",
            "config_hash": f"sha256:{manifest_hash}",
            "replayable": True,
            "created_at": timestamp,
        },
        "notes": f"Projection-loss report generated with max severity {severity_max(loss_items)}.",
    }
    return report, blocking


def build_receipt(report: Dict[str, Any], source_path: Path, manifest_path: Path, source_hash: str, manifest_hash: str, timestamp: str, out_dir: Path) -> Dict[str, Any]:
    report_hash = sha256_json(report)
    return {
        "receipt_id": report["receipt_ref"],
        "kind": "Receipt",
        "receipt_type": "PROJECTION",
        "created_at": timestamp,
        "compiler": {
            "name": "projection-loss-report-pack",
            "version": "0.1.0",
            "commit_sha": "unreleased-pack-v0.1",
            "runtime": "python-stdlib",
        },
        "ontology_profile": {
            "profile_id": "ontogenesis.shir.v0.1",
            "version": "0.1.0-draft",
            "module_refs": ["https://github.com/SocioProphet/ontogenesis/blob/main/docs/specs/shir-v0.1.md"],
            "shape_refs": ["shapes://pending/shir-core"],
        },
        "source_hashes": [
            {"algorithm": "sha256", "value": source_hash, "artifact_ref": str(source_path)},
            {"algorithm": "sha256", "value": manifest_hash, "artifact_ref": str(manifest_path)},
        ],
        "transform": {
            "transform_id": "transform.projection_loss_report.v0.1",
            "transform_type": "VALIDATION",
            "config_hash": CONFIG_HASH,
            "parameters": {
                "source_representation": report["source_representation"],
                "target_representation": report["target_representation"],
                "max_severity": severity_max(report["loss_items"]),
            },
        },
        "policy_decision": {
            "decision": "REVIEW_REQUIRED" if any(item.get("severity") == "BLOCKING" for item in report["loss_items"]) else "ALLOW",
            "policy_basis": report["governance"]["policy_basis"],
            "decided_at": timestamp,
            "decision_ref": f"policy.decision.projection_loss.{manifest_hash[:12]}",
        },
        "projection_loss_report_ref": report["report_id"],
        "semantic_leakage_checked": bool(report["semantic_leakage"]["checked"]),
        "outputs": [
            {
                "artifact_ref": str(out_dir / "projection_loss_report.json"),
                "artifact_type": "PROJECTION_LOSS_REPORT",
                "hash": {
                    "algorithm": "sha256",
                    "value": report_hash,
                    "artifact_ref": str(out_dir / "projection_loss_report.json"),
                },
            }
        ],
        "replay": {
            "replayable": True,
            "inputs_hash": f"sha256:{source_hash}",
            "config_hash": f"sha256:{manifest_hash}",
            "deterministic_seed": 7,
            "environment_ref": "python-stdlib",
        },
        "notes": "Receipt binds projection-loss report to source SHIR assertion, projection manifest, policy decision, and replay metadata.",
    }


def validate_outputs(schema_dir: Path, out_dir: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise SystemExit(f"jsonschema is required for --schema-dir validation: {exc}") from exc

    pairs = [
        ("shir_projection_loss_report.schema.json", "projection_loss_report.json"),
        ("shir_receipt.schema.json", "receipt.json"),
    ]
    for schema_name, output_name in pairs:
        schema = load_json(schema_dir / schema_name)
        instance = load_json(out_dir / output_name)
        jsonschema.validate(instance=instance, schema=schema)
        print(f"OK  {output_name}  against  {schema_name}")


def compile_report(source_path: Path, manifest_path: Path, out_dir: Path, timestamp: str, schema_dir: Optional[Path]) -> bool:
    source_text = source_path.read_text(encoding="utf-8")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    source = json.loads(source_text)
    manifest = json.loads(manifest_text)
    source_hash = sha256_text(source_text)
    manifest_hash = sha256_text(manifest_text)
    report, blocking = build_report(source, manifest, source_hash, manifest_hash, timestamp)
    receipt = build_receipt(report, source_path, manifest_path, source_hash, manifest_hash, timestamp, out_dir)
    write_json(out_dir / "projection_loss_report.json", report)
    write_json(out_dir / "receipt.json", receipt)
    if schema_dir:
        validate_outputs(schema_dir, out_dir)
    return blocking


def build_error_artifact(source_path: Path, manifest_path: Path, timestamp: str, error: Exception) -> Dict[str, Any]:
    return {
        "kind": "ProjectionLossCompileError",
        "created_at": timestamp,
        "compiler": {
            "name": "projection-loss-report-pack",
            "version": "0.1.0",
            "runtime": "python-stdlib",
        },
        "source_ref": str(source_path),
        "manifest_ref": str(manifest_path),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "policy_decision": "QUARANTINE",
        "replay": {
            "replayable": source_path.exists() and manifest_path.exists(),
            "config_hash": CONFIG_HASH,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a SHIR projection-loss report and receipt.")
    parser.add_argument("--source-shir", required=True, help="Source SHIR assertion JSON")
    parser.add_argument("--projection-manifest", required=True, help="Projection manifest JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--schema-dir", help="Optional semantic-serdes schema directory")
    parser.add_argument("--timestamp", default=DEFAULT_TIMESTAMP, help="Deterministic timestamp for generated artifacts")
    parser.add_argument("--fail-on-blocking", action="store_true", help="Exit 2 when a blocking loss is detected")
    args = parser.parse_args()

    source_path = Path(args.source_shir)
    manifest_path = Path(args.projection_manifest)
    out_dir = Path(args.out_dir)
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        blocking = compile_report(source_path, manifest_path, out_dir, args.timestamp, schema_dir)
        print(json.dumps({"out_dir": str(out_dir), "blocking": blocking}, indent=2, sort_keys=True))
        if blocking and args.fail_on_blocking:
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must fail closed with artifact.
        write_json(out_dir / "compile_error.json", build_error_artifact(source_path, manifest_path, args.timestamp, exc))
        print(f"projection-loss compile failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
