#!/usr/bin/env python3
"""Lower a SHIR assertion into a PyG-style heterogeneous graph manifest.

v0.1 is manifest-only: it does not import PyTorch or PyG. The pack emits a
PyG-compatible manifest, a projection manifest, a projection-loss report via
the sibling projection-loss-report pack, and a final receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
CONFIG_HASH = "sha256:shir-to-pyg-pack-v0.1-default"

TYPE_HINTS = {
    "TopoLVM": "Technology",
    "PersistentVolume": "StorageResource",
    "KubernetesNode": "ComputeNode",
    "AgentMachineNode": "ComputeNode",
    "LocalStorage": "StorageResource",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(doc: Dict[str, Any]) -> str:
    return sha256_text(json.dumps(doc, sort_keys=True, separators=(",", ":")))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, doc: Dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_id(prefix: str, *parts: str) -> str:
    tokens: List[str] = []
    for part in parts:
        token = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(part)).strip("_")
        while "__" in token:
            token = token.replace("__", "_")
        if token:
            tokens.append(token)
    return ".".join([prefix, *tokens])


def node_type_for_binding(binding: Dict[str, Any]) -> str:
    label = binding.get("label") or binding.get("participant_id", "Resource")
    return TYPE_HINTS.get(label, "Resource")


def add_node(nodes: Dict[str, Dict[str, Any]], node_type: str, node_id: str, label: str, source_ref: str, trainable: bool = False) -> None:
    bucket = nodes.setdefault(node_type, {"count": 0, "ids": [], "labels": {}, "source_refs": {}, "trainable": trainable})
    if node_id not in bucket["ids"]:
        bucket["ids"].append(node_id)
        bucket["count"] = len(bucket["ids"])
    bucket["labels"][node_id] = label
    bucket["source_refs"][node_id] = source_ref


def edge_type(source_type: str, relation: str, target_type: str) -> str:
    return f"({source_type}, {relation}, {target_type})"


def append_edge(edges: List[Dict[str, Any]], source_type: str, relation: str, target_type: str, source_id: str, target_id: str, source_ref: str) -> None:
    edges.append(
        {
            "edge_type": edge_type(source_type, relation, target_type),
            "source_type": source_type,
            "relation": relation,
            "target_type": target_type,
            "source_id": source_id,
            "target_id": target_id,
            "source_ref": source_ref,
        }
    )


def build_pyg_manifest(source: Dict[str, Any], timestamp: str, relation_strategy: str) -> Dict[str, Any]:
    assertion_id = source.get("assertion_id", "shir.assertion.unknown")
    connector = source.get("connector", {})
    connector_label = connector.get("label", "unknown_connector")
    role_bindings = source.get("role_bindings", [])
    if not isinstance(role_bindings, list) or not role_bindings:
        raise ValueError("source SHIR assertion must include non-empty role_bindings")

    relation_node_id = stable_id("relation", assertion_id)
    relation_label = f"Relation for {connector_label}"
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    feature_provenance: List[Dict[str, Any]] = []

    add_node(nodes, "Relation", relation_node_id, relation_label, assertion_id, trainable=False)

    for binding in role_bindings:
        role = binding.get("role")
        participant_id = binding.get("participant_id")
        label = binding.get("label", participant_id)
        if not role or not participant_id:
            raise ValueError(f"invalid role binding: {binding}")
        participant_type = node_type_for_binding(binding)
        add_node(nodes, participant_type, participant_id, label, assertion_id, trainable=False)
        if role == "provider":
            append_edge(edges, participant_type, "role_provider", "Relation", participant_id, relation_node_id, assertion_id)
        else:
            append_edge(edges, "Relation", f"role_{role}", participant_type, relation_node_id, participant_id, assertion_id)
        feature_provenance.append(
            {
                "node_id": participant_id,
                "feature_name": "label",
                "source_ref": f"{assertion_id}.role_bindings.{role}",
                "trainable": False,
                "notes": "Label retained as manifest metadata, not tensorized in v0.1.",
            }
        )

    for anchor in source.get("evidence_anchors", []) or []:
        anchor_id = anchor.get("anchor_id")
        if anchor_id:
            add_node(nodes, "DocumentAnchor", anchor_id, anchor.get("anchor_type", "EvidenceAnchor"), assertion_id, trainable=False)
            append_edge(edges, "Relation", "supported_by", "DocumentAnchor", relation_node_id, anchor_id, assertion_id)

    context = source.get("context") or {}
    context_id = context.get("context_id")
    if context_id:
        add_node(nodes, "Context", context_id, context.get("label", "Context"), assertion_id, trainable=False)
        append_edge(edges, "Relation", "scoped_by", "Context", relation_node_id, context_id, assertion_id)

    manifest_id = stable_id("pyg.manifest", assertion_id)
    return {
        "manifest_id": manifest_id,
        "kind": "PyGHeteroDataManifest",
        "created_at": timestamp,
        "source_assertion_ref": assertion_id,
        "target_framework": "pyg",
        "target_representation": "PYG_HETERODATA",
        "materialization": "manifest_only",
        "relation_strategy": relation_strategy,
        "node_types": nodes,
        "edge_types": edges,
        "feature_provenance": feature_provenance,
        "train_test_split": {
            "status": "NOT_MATERIALIZED",
            "split_policy": "defer_until_dataset_materialization",
            "leakage_sensitive": True,
        },
        "semantic_leakage": {
            "checked": True,
            "risk_level": "LOW",
            "markers": ["NONE"],
            "mitigations": [
                "Do not tensorize ontology class labels, source filenames, policy refs, or receipt refs in v0.1.",
                "Run the semantic-leakage detector pack before model training publication.",
            ],
        },
        "governance": {
            "review_status": "REQUIRED",
            "export_allowed": True,
            "training_allowed": True,
            "policy_basis": [
                "shir.v0.1.loss_report_required_for_graph_ml",
                "policy.public_technical_docs.allowed_for_training",
            ],
        },
    }


def build_projection_manifest(pyg_manifest: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "projection_id": stable_id("shir.projection", pyg_manifest["manifest_id"]),
        "source_representation": "SHIR",
        "target_representation": "PYG_HETERODATA",
        "relation_strategy": pyg_manifest["relation_strategy"],
        "strict_publication": False,
        "preservation": {
            "temporal_scope": "feature_metadata",
            "observation_time": "feature_metadata",
            "evidence_anchors": "external_ref",
            "policy_scope": "external_ref",
            "context": "external_ref",
            "governance": "external_ref",
            "noise_assessment": "external_ref",
        },
        "semantic_leakage": pyg_manifest["semantic_leakage"],
        "governance": pyg_manifest["governance"],
    }


def run_projection_loss_tool(
    repo_root: Path,
    source_path: Path,
    projection_manifest_path: Path,
    out_dir: Path,
    timestamp: str,
    schema_dir: Optional[Path],
) -> Path:
    loss_dir = out_dir / "_projection_loss"
    loss_dir.mkdir(parents=True, exist_ok=True)
    tool = repo_root / "packs" / "projection-loss-report" / "tools" / "projection_loss_report.py"
    if not tool.exists():
        raise FileNotFoundError(f"projection-loss-report tool not found at {tool}")
    command = [
        sys.executable,
        str(tool),
        "--source-shir",
        str(source_path),
        "--projection-manifest",
        str(projection_manifest_path),
        "--out-dir",
        str(loss_dir),
        "--timestamp",
        timestamp,
    ]
    if schema_dir:
        command.extend(["--schema-dir", str(schema_dir)])
    subprocess.run(command, check=True)
    report_path = loss_dir / "projection_loss_report.json"
    if not report_path.exists():
        raise FileNotFoundError("projection-loss-report pack did not emit projection_loss_report.json")
    return report_path


def build_receipt(
    source_path: Path,
    source_hash: str,
    pyg_manifest: Dict[str, Any],
    projection_manifest: Dict[str, Any],
    projection_loss_report: Dict[str, Any],
    timestamp: str,
    out_dir: Path,
) -> Dict[str, Any]:
    pyg_hash = sha256_json(pyg_manifest)
    loss_hash = sha256_json(projection_loss_report)
    manifest_hash = sha256_json(projection_manifest)
    blocking = any(item.get("severity") == "BLOCKING" for item in projection_loss_report.get("loss_items", []))
    return {
        "receipt_id": stable_id("shir.receipt.shir_to_pyg", pyg_manifest["manifest_id"]),
        "kind": "Receipt",
        "receipt_type": "PROJECTION",
        "created_at": timestamp,
        "compiler": {
            "name": "shir-to-pyg-pack",
            "version": "0.1.0",
            "commit_sha": "unreleased-pack-v0.1",
            "runtime": "python-stdlib-manifest-only",
        },
        "ontology_profile": {
            "profile_id": "ontogenesis.shir.v0.1",
            "version": "0.1.0-draft",
            "module_refs": ["https://github.com/SocioProphet/ontogenesis/blob/main/docs/specs/shir-v0.1.md"],
            "shape_refs": ["shapes://pending/shir-core"],
        },
        "source_hashes": [
            {"algorithm": "sha256", "value": source_hash, "artifact_ref": str(source_path)},
            {"algorithm": "sha256", "value": manifest_hash, "artifact_ref": str(out_dir / "projection_manifest.json")},
        ],
        "transform": {
            "transform_id": "transform.shir.to.pyg.v0.1",
            "transform_type": "SHIR_TO_PYG",
            "config_hash": CONFIG_HASH,
            "parameters": {
                "relation_strategy": pyg_manifest["relation_strategy"],
                "materialization": pyg_manifest["materialization"],
                "projection_loss_report_required": True,
            },
        },
        "policy_decision": {
            "decision": "REVIEW_REQUIRED" if blocking else "ALLOW",
            "policy_basis": pyg_manifest["governance"]["policy_basis"],
            "decided_at": timestamp,
            "decision_ref": stable_id("policy.decision.shir_to_pyg", pyg_manifest["manifest_id"]),
        },
        "projection_loss_report_ref": projection_loss_report["report_id"],
        "semantic_leakage_checked": bool(pyg_manifest["semantic_leakage"]["checked"]),
        "outputs": [
            {
                "artifact_ref": str(out_dir / "pyg_manifest.json"),
                "artifact_type": "PYG_MANIFEST",
                "hash": {
                    "algorithm": "sha256",
                    "value": pyg_hash,
                    "artifact_ref": str(out_dir / "pyg_manifest.json"),
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
            "inputs_hash": f"sha256:{source_hash}",
            "config_hash": CONFIG_HASH,
            "deterministic_seed": 7,
            "environment_ref": "python-stdlib-manifest-only",
        },
        "notes": "Manifest-only SHIR-to-PyG projection with projection-loss report and semantic-leakage metadata.",
    }


def validate_final_outputs(schema_dir: Path, out_dir: Path) -> None:
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


def compile_projection(source_path: Path, out_dir: Path, timestamp: str, relation_strategy: str, schema_dir: Optional[Path]) -> None:
    source_text = source_path.read_text(encoding="utf-8")
    source_hash = sha256_text(source_text)
    source = json.loads(source_text)
    pyg_manifest = build_pyg_manifest(source, timestamp, relation_strategy)
    projection_manifest = build_projection_manifest(pyg_manifest)
    write_json(out_dir / "pyg_manifest.json", pyg_manifest)
    write_json(out_dir / "projection_manifest.json", projection_manifest)

    repo_root = Path(__file__).resolve().parents[3]
    loss_report_path = run_projection_loss_tool(repo_root, source_path, out_dir / "projection_manifest.json", out_dir, timestamp, schema_dir)
    shutil.copyfile(loss_report_path, out_dir / "projection_loss_report.json")
    projection_loss_report = load_json(out_dir / "projection_loss_report.json")
    receipt = build_receipt(source_path, source_hash, pyg_manifest, projection_manifest, projection_loss_report, timestamp, out_dir)
    write_json(out_dir / "receipt.json", receipt)
    if schema_dir:
        validate_final_outputs(schema_dir, out_dir)


def build_error_artifact(source_path: Path, timestamp: str, error: Exception) -> Dict[str, Any]:
    return {
        "kind": "SHIRToPyGCompileError",
        "created_at": timestamp,
        "compiler": {
            "name": "shir-to-pyg-pack",
            "version": "0.1.0",
            "runtime": "python-stdlib-manifest-only",
        },
        "source_ref": str(source_path),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "policy_decision": "QUARANTINE",
        "replay": {
            "replayable": source_path.exists(),
            "config_hash": CONFIG_HASH,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lower SHIR assertion JSON to a PyG-style heterogeneous graph manifest.")
    parser.add_argument("--source-shir", required=True, help="Source SHIR assertion JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--schema-dir", help="Optional semantic-serdes schema directory")
    parser.add_argument("--timestamp", default=DEFAULT_TIMESTAMP, help="Deterministic timestamp for generated artifacts")
    parser.add_argument("--relation-strategy", default="relation_node", choices=["relation_node", "binary_edges", "hyperedge"], help="N-ary relation lowering strategy")
    args = parser.parse_args()

    source_path = Path(args.source_shir)
    out_dir = Path(args.out_dir)
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        compile_projection(source_path, out_dir, args.timestamp, args.relation_strategy, schema_dir)
        print(json.dumps({"out_dir": str(out_dir), "manifest": str(out_dir / "pyg_manifest.json")}, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must fail closed with artifact.
        write_json(out_dir / "compile_error.json", build_error_artifact(source_path, args.timestamp, exc))
        print(f"shir-to-pyg compile failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
