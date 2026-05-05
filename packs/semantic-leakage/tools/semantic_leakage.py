#!/usr/bin/env python3
"""Detect semantic leakage in SHIR-derived projection manifests.

The detector is runtime-light and manifest-oriented. It emits a native
semantic_leakage_report plus semantic-serdes-compatible ProjectionLossReport
and Receipt artifacts so downstream gates can reuse the SHIR governance lane.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
CONFIG_HASH = "sha256:semantic-leakage-pack-v0.1-default"
SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "BLOCKING": 4}
RISK_BY_SEVERITY = {
    "INFO": "NONE",
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "BLOCKING": "BLOCKING",
}
LEAKAGE_TO_DIMENSION = {
    "RDF_TYPE_LABEL": "CONTEXT",
    "ONTOLOGY_HIERARCHY": "CONTEXT",
    "GRAPH_PARTITION": "NAMED_GRAPH",
    "SOURCE_FILENAME": "PROVENANCE",
    "FUTURE_TIMESTAMP": "TEMPORAL_SCOPE",
    "PROVENANCE_FIELD": "PROVENANCE",
    "NAMING_CONVENTION": "IDENTITY_CANONICALIZATION",
    "TARGET_PROPERTY": "PROVENANCE",
    "TRAIN_TEST_CONTAMINATION": "PROVENANCE",
}
LEAKAGE_SEVERITY = {
    "RDF_TYPE_LABEL": "HIGH",
    "ONTOLOGY_HIERARCHY": "HIGH",
    "GRAPH_PARTITION": "MEDIUM",
    "SOURCE_FILENAME": "MEDIUM",
    "FUTURE_TIMESTAMP": "BLOCKING",
    "PROVENANCE_FIELD": "MEDIUM",
    "NAMING_CONVENTION": "MEDIUM",
    "TARGET_PROPERTY": "BLOCKING",
    "TRAIN_TEST_CONTAMINATION": "BLOCKING",
}

SENSITIVE_FEATURE_TOKENS = {
    "rdf_type": "RDF_TYPE_LABEL",
    "rdf:type": "RDF_TYPE_LABEL",
    "type_label": "RDF_TYPE_LABEL",
    "class_label": "RDF_TYPE_LABEL",
    "ontology_hierarchy": "ONTOLOGY_HIERARCHY",
    "subclass": "ONTOLOGY_HIERARCHY",
    "superclass": "ONTOLOGY_HIERARCHY",
    "graph_partition": "GRAPH_PARTITION",
    "graph_name": "GRAPH_PARTITION",
    "source_filename": "SOURCE_FILENAME",
    "filename": "SOURCE_FILENAME",
    "path": "SOURCE_FILENAME",
    "provenance": "PROVENANCE_FIELD",
    "source_ref": "PROVENANCE_FIELD",
    "receipt_ref": "PROVENANCE_FIELD",
    "target": "TARGET_PROPERTY",
    "label_target": "TARGET_PROPERTY",
    "ground_truth": "TARGET_PROPERTY",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(doc: Dict[str, Any]) -> str:
    return sha256_text(json.dumps(doc, sort_keys=True, separators=(",", ":")))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, doc: Dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_dt(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def max_severity(findings: Iterable[Dict[str, Any]]) -> str:
    max_name = "INFO"
    max_value = SEVERITY_ORDER[max_name]
    for finding in findings:
        value = SEVERITY_ORDER.get(finding.get("severity", "INFO"), 0)
        if value > max_value:
            max_name = finding.get("severity", "INFO")
            max_value = value
    return max_name


def marker_for_feature_name(name: str) -> Optional[str]:
    lowered = name.lower()
    for token, marker in SENSITIVE_FEATURE_TOKENS.items():
        if token in lowered:
            return marker
    return None


def add_finding(findings: List[Dict[str, Any]], marker: str, location: str, explanation: str) -> None:
    findings.append(
        {
            "marker": marker,
            "severity": LEAKAGE_SEVERITY[marker],
            "location": location,
            "explanation": explanation,
            "mitigation": mitigation_for(marker),
        }
    )


def mitigation_for(marker: str) -> str:
    return {
        "RDF_TYPE_LABEL": "Remove RDF/type/class-label features from trainable tensors unless the task explicitly predicts type and split design prevents leakage.",
        "ONTOLOGY_HIERARCHY": "Remove direct ontology ancestry features or isolate them behind a task-specific ablation and leakage receipt.",
        "GRAPH_PARTITION": "Do not use graph names or partition IDs as trainable features unless partition is part of the legitimate prediction input.",
        "SOURCE_FILENAME": "Strip source filenames and path-derived metadata from trainable features.",
        "FUTURE_TIMESTAMP": "Remove or censor timestamps later than the prediction cutoff before training/export.",
        "PROVENANCE_FIELD": "Keep provenance, source refs, and receipt refs outside trainable tensors unless governance prediction is the explicit task.",
        "NAMING_CONVENTION": "Hash or remove IDs/names that encode target classes, outcomes, splits, or policy labels.",
        "TARGET_PROPERTY": "Remove target/ground-truth fields from feature manifests before training.",
        "TRAIN_TEST_CONTAMINATION": "Recompute splits by stable entity ID, provenance group, and temporal cutoff to prevent duplicated train/test rows.",
    }[marker]


def scan_feature_provenance(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    features = manifest.get("feature_provenance", []) or []
    if not isinstance(features, list):
        add_finding(findings, "PROVENANCE_FIELD", "feature_provenance", "feature_provenance is not a list; cannot safely audit features.")
        return findings

    for idx, feature in enumerate(features):
        if not isinstance(feature, dict):
            continue
        trainable = bool(feature.get("trainable", True))
        name = str(feature.get("feature_name", ""))
        source_ref = str(feature.get("source_ref", ""))
        location = f"feature_provenance[{idx}]"
        if trainable:
            marker = marker_for_feature_name(name) or marker_for_feature_name(source_ref)
            if marker:
                add_finding(findings, marker, location, f"Trainable feature {name!r} or source_ref {source_ref!r} appears to encode {marker}.")
        if "target" in name.lower() and trainable:
            add_finding(findings, "TARGET_PROPERTY", location, f"Trainable feature {name!r} appears to encode a target property.")
    return findings


def scan_nodes_and_edges(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    node_types = manifest.get("node_types", {}) or {}
    if isinstance(node_types, dict):
        for node_type, bucket in node_types.items():
            if not isinstance(bucket, dict):
                continue
            trainable = bool(bucket.get("trainable", False))
            if trainable and node_type in {"Relation", "Context", "DocumentAnchor"}:
                add_finding(findings, "PROVENANCE_FIELD", f"node_types.{node_type}", f"Governance/context/evidence node type {node_type!r} is marked trainable.")
            for node_id in bucket.get("ids", []) or []:
                lowered = str(node_id).lower()
                if any(token in lowered for token in ["target", "ground_truth", "label"]):
                    add_finding(findings, "NAMING_CONVENTION", f"node_types.{node_type}.ids", f"Node id {node_id!r} appears to encode a target or label naming convention.")
    edge_types = manifest.get("edge_types", []) or []
    if isinstance(edge_types, list):
        for idx, edge in enumerate(edge_types):
            if not isinstance(edge, dict):
                continue
            relation = str(edge.get("relation", "")).lower()
            if "target" in relation or "ground_truth" in relation:
                add_finding(findings, "TARGET_PROPERTY", f"edge_types[{idx}]", f"Edge relation {relation!r} appears to encode target information.")
    return findings


def scan_split(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    split = manifest.get("train_test_split", {}) or {}
    if not isinstance(split, dict):
        add_finding(findings, "TRAIN_TEST_CONTAMINATION", "train_test_split", "train_test_split is not an object; cannot verify contamination controls.")
        return findings
    train_ids = set(split.get("train_ids", []) or [])
    test_ids = set(split.get("test_ids", []) or [])
    overlap = train_ids.intersection(test_ids)
    if overlap:
        add_finding(findings, "TRAIN_TEST_CONTAMINATION", "train_test_split", f"Train/test split shares IDs: {sorted(overlap)}")
    if split.get("status") == "MATERIALIZED" and not split.get("grouping_key"):
        add_finding(findings, "TRAIN_TEST_CONTAMINATION", "train_test_split.grouping_key", "Materialized split lacks a grouping key for entity/provenance-level deduplication.")
    return findings


def scan_temporal(manifest: Dict[str, Any], prediction_cutoff: Optional[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    if not prediction_cutoff:
        return findings
    cutoff = parse_dt(prediction_cutoff)
    timestamps = manifest.get("temporal_features", []) or []
    if not isinstance(timestamps, list):
        add_finding(findings, "FUTURE_TIMESTAMP", "temporal_features", "temporal_features is not a list; cannot audit future timestamp leakage.")
        return findings
    for idx, feature in enumerate(timestamps):
        if not isinstance(feature, dict):
            continue
        value = feature.get("value")
        trainable = bool(feature.get("trainable", True))
        if value and trainable:
            try:
                parsed = parse_dt(str(value))
            except ValueError:
                continue
            if parsed > cutoff:
                add_finding(findings, "FUTURE_TIMESTAMP", f"temporal_features[{idx}]", f"Trainable timestamp {value!r} is later than prediction cutoff {prediction_cutoff!r}.")
    return findings


def scan_manifest(manifest: Dict[str, Any], prediction_cutoff: Optional[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    findings.extend(scan_feature_provenance(manifest))
    findings.extend(scan_nodes_and_edges(manifest))
    findings.extend(scan_split(manifest))
    findings.extend(scan_temporal(manifest, prediction_cutoff))
    declared = manifest.get("semantic_leakage", {}) or {}
    if isinstance(declared, dict):
        for marker in declared.get("markers", []) or []:
            if marker != "NONE" and marker in LEAKAGE_SEVERITY:
                add_finding(findings, marker, "semantic_leakage.markers", f"Projection manifest already declares leakage marker {marker}.")
    return findings


def unique_markers(findings: List[Dict[str, Any]]) -> List[str]:
    markers: List[str] = []
    seen: Set[str] = set()
    for finding in findings:
        marker = finding["marker"]
        if marker not in seen:
            seen.add(marker)
            markers.append(marker)
    return markers or ["NONE"]


def build_native_report(manifest: Dict[str, Any], manifest_hash: str, findings: List[Dict[str, Any]], prediction_cutoff: Optional[str], timestamp: str) -> Dict[str, Any]:
    severity = max_severity(findings)
    markers = unique_markers(findings)
    return {
        "report_id": f"semantic.leakage.{manifest_hash[:12]}",
        "kind": "SemanticLeakageReport",
        "created_at": timestamp,
        "manifest_ref": manifest.get("manifest_id", manifest.get("projection_id", "manifest.unknown")),
        "prediction_cutoff": prediction_cutoff,
        "risk_level": RISK_BY_SEVERITY[severity],
        "markers": markers,
        "findings": findings,
        "mitigations": sorted({finding["mitigation"] for finding in findings}) if findings else [],
        "summary": "No semantic leakage detected." if not findings else f"Detected {len(findings)} semantic leakage finding(s).",
    }


def build_projection_loss_report(manifest: Dict[str, Any], native_report: Dict[str, Any], manifest_hash: str, timestamp: str) -> Dict[str, Any]:
    markers = native_report["markers"]
    findings = native_report["findings"]
    loss_items: List[Dict[str, Any]] = []
    if findings:
        for idx, finding in enumerate(findings):
            marker = finding["marker"]
            loss_items.append(
                {
                    "semantic_dimension": LEAKAGE_TO_DIMENSION[marker],
                    "loss_mode": "PRESERVED" if finding["severity"] in {"INFO", "LOW"} else "APPROXIMATED",
                    "source_ref": finding["location"],
                    "target_ref": manifest.get("manifest_id", manifest.get("projection_id", "manifest.unknown")),
                    "explanation": finding["explanation"],
                    "severity": finding["severity"],
                }
            )
    else:
        loss_items.append(
            {
                "semantic_dimension": "PROVENANCE",
                "loss_mode": "PRESERVED",
                "source_ref": manifest.get("manifest_id", manifest.get("projection_id", "manifest.unknown")),
                "target_ref": native_report["report_id"],
                "explanation": "Semantic leakage detector found no leakage markers in audited manifest fields.",
                "severity": "INFO",
            }
        )

    blocking = any(item["severity"] == "BLOCKING" for item in loss_items)
    return {
        "report_id": f"shir.loss.semantic_leakage.{manifest_hash[:12]}",
        "kind": "ProjectionLossReport",
        "projection_ref": manifest.get("manifest_id", manifest.get("projection_id", f"projection.{manifest_hash[:12]}")),
        "source_representation": manifest.get("source_representation", "SHIR"),
        "target_representation": manifest.get("target_representation", "PYG_HETERODATA"),
        "loss_items": loss_items,
        "semantic_leakage": {
            "checked": True,
            "risk_level": native_report["risk_level"],
            "markers": markers,
            "mitigations": native_report["mitigations"],
        },
        "governance": {
            "review_status": "ESCALATED" if blocking else ("REQUIRED" if findings else "NOT_REQUIRED"),
            "export_allowed": not blocking,
            "training_allowed": not blocking,
            "policy_basis": ["shir.v0.1.semantic_leakage_detection_required"],
        },
        "receipt_ref": f"shir.receipt.semantic_leakage.{manifest_hash[:12]}",
        "replay": {
            "inputs_hash": f"sha256:{manifest_hash}",
            "config_hash": CONFIG_HASH,
            "replayable": True,
            "created_at": timestamp,
        },
        "notes": native_report["summary"],
    }


def build_receipt(manifest_path: Path, manifest_hash: str, native_report: Dict[str, Any], loss_report: Dict[str, Any], timestamp: str, out_dir: Path) -> Dict[str, Any]:
    native_hash = sha256_json(native_report)
    loss_hash = sha256_json(loss_report)
    blocking = any(item.get("severity") == "BLOCKING" for item in loss_report["loss_items"])
    return {
        "receipt_id": loss_report["receipt_ref"],
        "kind": "Receipt",
        "receipt_type": "VALIDATION",
        "created_at": timestamp,
        "compiler": {
            "name": "semantic-leakage-pack",
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
            {"algorithm": "sha256", "value": manifest_hash, "artifact_ref": str(manifest_path)}
        ],
        "transform": {
            "transform_id": "transform.semantic_leakage.v0.1",
            "transform_type": "VALIDATION",
            "config_hash": CONFIG_HASH,
            "parameters": {
                "risk_level": native_report["risk_level"],
                "markers": native_report["markers"],
            },
        },
        "policy_decision": {
            "decision": "REVIEW_REQUIRED" if blocking else "ALLOW",
            "policy_basis": loss_report["governance"]["policy_basis"],
            "decided_at": timestamp,
            "decision_ref": f"policy.decision.semantic_leakage.{manifest_hash[:12]}",
        },
        "projection_loss_report_ref": loss_report["report_id"],
        "semantic_leakage_checked": True,
        "outputs": [
            {
                "artifact_ref": str(out_dir / "semantic_leakage_report.json"),
                "artifact_type": "VALIDATION_REPORT",
                "hash": {
                    "algorithm": "sha256",
                    "value": native_hash,
                    "artifact_ref": str(out_dir / "semantic_leakage_report.json"),
                },
            },
            {
                "artifact_ref": str(out_dir / "projection_loss_report.json"),
                "artifact_type": "PROJECTION_LOSS_REPORT",
                "hash": {
                    "algorithm": "sha256",
                    "value": loss_hash,
                    "artifact_ref": str(out_dir / "projection_loss_report.json"),
                },
            },
        ],
        "replay": {
            "replayable": True,
            "inputs_hash": f"sha256:{manifest_hash}",
            "config_hash": CONFIG_HASH,
            "deterministic_seed": 7,
            "environment_ref": "python-stdlib",
        },
        "notes": native_report["summary"],
    }


def validate_outputs(schema_dir: Path, out_dir: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise SystemExit(f"jsonschema is required for --schema-dir validation: {exc}") from exc
    for schema_name, output_name in [
        ("shir_projection_loss_report.schema.json", "projection_loss_report.json"),
        ("shir_receipt.schema.json", "receipt.json"),
    ]:
        schema = load_json(schema_dir / schema_name)
        instance = load_json(out_dir / output_name)
        jsonschema.validate(instance=instance, schema=schema)
        print(f"OK  {output_name}  against  {schema_name}")


def compile_report(manifest_path: Path, out_dir: Path, timestamp: str, prediction_cutoff: Optional[str], schema_dir: Optional[Path]) -> bool:
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_hash = sha256_text(manifest_text)
    manifest = json.loads(manifest_text)
    findings = scan_manifest(manifest, prediction_cutoff)
    native_report = build_native_report(manifest, manifest_hash, findings, prediction_cutoff, timestamp)
    loss_report = build_projection_loss_report(manifest, native_report, manifest_hash, timestamp)
    receipt = build_receipt(manifest_path, manifest_hash, native_report, loss_report, timestamp, out_dir)
    write_json(out_dir / "semantic_leakage_report.json", native_report)
    write_json(out_dir / "projection_loss_report.json", loss_report)
    write_json(out_dir / "receipt.json", receipt)
    if schema_dir:
        validate_outputs(schema_dir, out_dir)
    return any(item.get("severity") == "BLOCKING" for item in loss_report["loss_items"])


def build_error_artifact(manifest_path: Path, timestamp: str, error: Exception) -> Dict[str, Any]:
    return {
        "kind": "SemanticLeakageCompileError",
        "created_at": timestamp,
        "compiler": {
            "name": "semantic-leakage-pack",
            "version": "0.1.0",
            "runtime": "python-stdlib",
        },
        "manifest_ref": str(manifest_path),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "policy_decision": "QUARANTINE",
        "replay": {
            "replayable": manifest_path.exists(),
            "config_hash": CONFIG_HASH,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect semantic leakage in a SHIR-derived projection manifest.")
    parser.add_argument("--manifest", required=True, help="Projection manifest to audit")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--schema-dir", help="Optional semantic-serdes schema directory")
    parser.add_argument("--prediction-cutoff", help="Optional prediction cutoff timestamp for temporal leakage checks")
    parser.add_argument("--timestamp", default=DEFAULT_TIMESTAMP, help="Deterministic timestamp for generated artifacts")
    parser.add_argument("--fail-on-blocking", action="store_true", help="Exit 2 when a blocking leakage finding is detected")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_dir = Path(args.out_dir)
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        blocking = compile_report(manifest_path, out_dir, args.timestamp, args.prediction_cutoff, schema_dir)
        print(json.dumps({"out_dir": str(out_dir), "blocking": blocking}, indent=2, sort_keys=True))
        if blocking and args.fail_on_blocking:
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must fail closed with artifact.
        write_json(out_dir / "compile_error.json", build_error_artifact(manifest_path, args.timestamp, exc))
        print(f"semantic-leakage compile failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
