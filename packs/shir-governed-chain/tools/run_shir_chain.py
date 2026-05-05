#!/usr/bin/env python3
"""Run the governed SHIR demo chain end to end.

Chain:
  rdf-to-shir -> shir-to-pyg -> semantic-leakage -> chain receipt

The chain is manifest-only and deterministic by default. It emits a final
receipt summarizing hashes, stage receipts, policy decision, and replay data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
CONFIG_HASH = "sha256:shir-governed-chain-v0.1-default"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(doc: Dict[str, Any]) -> str:
    return sha256_text(json.dumps(doc, sort_keys=True, separators=(",", ":")))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, doc: Dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_cmd(args: List[str]) -> None:
    subprocess.run(args, check=True)


def run_rdf_to_shir(root: Path, input_path: Path, out_dir: Path, timestamp: str, schema_dir: Optional[Path]) -> None:
    cmd = [
        sys.executable,
        str(root / "packs" / "rdf-to-shir" / "tools" / "rdf_to_shir.py"),
        "--input",
        str(input_path),
        "--out-dir",
        str(out_dir),
        "--timestamp",
        timestamp,
    ]
    if schema_dir:
        cmd.extend(["--schema-dir", str(schema_dir)])
    run_cmd(cmd)


def run_shir_to_pyg(root: Path, source_shir: Path, out_dir: Path, timestamp: str, schema_dir: Optional[Path]) -> None:
    cmd = [
        sys.executable,
        str(root / "packs" / "shir-to-pyg" / "tools" / "shir_to_pyg.py"),
        "--source-shir",
        str(source_shir),
        "--out-dir",
        str(out_dir),
        "--timestamp",
        timestamp,
        "--relation-strategy",
        "relation_node",
    ]
    if schema_dir:
        cmd.extend(["--schema-dir", str(schema_dir)])
    run_cmd(cmd)


def run_semantic_leakage(root: Path, manifest: Path, out_dir: Path, timestamp: str, schema_dir: Optional[Path]) -> None:
    cmd = [
        sys.executable,
        str(root / "packs" / "semantic-leakage" / "tools" / "semantic_leakage.py"),
        "--manifest",
        str(manifest),
        "--out-dir",
        str(out_dir),
        "--timestamp",
        timestamp,
    ]
    if schema_dir:
        cmd.extend(["--schema-dir", str(schema_dir)])
    run_cmd(cmd)


def stage_hash(path: Path) -> Dict[str, str]:
    return {"artifact_ref": str(path), "algorithm": "sha256", "value": sha256_file(path)}


def build_chain_receipt(
    input_path: Path,
    out_dir: Path,
    timestamp: str,
    schema_dir: Optional[Path],
) -> Dict[str, Any]:
    rdf_dir = out_dir / "rdf-to-shir"
    pyg_dir = out_dir / "shir-to-pyg"
    leakage_dir = out_dir / "semantic-leakage"

    rdf_receipt = load_json(rdf_dir / "receipt.json")
    pyg_receipt = load_json(pyg_dir / "receipt.json")
    projection_loss = load_json(pyg_dir / "projection_loss_report.json")
    leakage_report = load_json(leakage_dir / "semantic_leakage_report.json")
    leakage_loss = load_json(leakage_dir / "projection_loss_report.json")
    leakage_receipt = load_json(leakage_dir / "receipt.json")

    blocking = (
        any(item.get("severity") == "BLOCKING" for item in projection_loss.get("loss_items", []))
        or any(item.get("severity") == "BLOCKING" for item in leakage_loss.get("loss_items", []))
    )
    policy_decision = "REVIEW_REQUIRED" if blocking else "ALLOW"

    output_artifacts = [
        (rdf_dir / "candidate_assertion.json", "SHIR_JSON"),
        (rdf_dir / "assertion.json", "SHIR_JSON"),
        (pyg_dir / "pyg_manifest.json", "PYG_MANIFEST"),
        (pyg_dir / "projection_loss_report.json", "PROJECTION_LOSS_REPORT"),
        (leakage_dir / "semantic_leakage_report.json", "VALIDATION_REPORT"),
        (leakage_dir / "projection_loss_report.json", "PROJECTION_LOSS_REPORT"),
    ]

    receipt = {
        "receipt_id": f"shir.receipt.governed_chain.{sha256_file(input_path)[:12]}",
        "kind": "Receipt",
        "receipt_type": "VALIDATION",
        "created_at": timestamp,
        "compiler": {
            "name": "shir-governed-chain",
            "version": "0.1.0",
            "commit_sha": "unreleased-chain-v0.1",
            "runtime": "python-stdlib-orchestrator",
        },
        "ontology_profile": {
            "profile_id": "ontogenesis.shir.v0.1",
            "version": "0.1.0-draft",
            "module_refs": ["https://github.com/SocioProphet/ontogenesis/blob/main/docs/specs/shir-v0.1.md"],
            "shape_refs": ["shapes://pending/shir-core"],
        },
        "source_hashes": [stage_hash(input_path)],
        "transform": {
            "transform_id": "transform.shir.governed_chain.v0.1",
            "transform_type": "VALIDATION",
            "config_hash": CONFIG_HASH,
            "parameters": {
                "stages": ["rdf-to-shir", "shir-to-pyg", "semantic-leakage"],
                "semantic_serdes_schema_validation": bool(schema_dir),
                "relation_strategy": "relation_node",
            },
        },
        "policy_decision": {
            "decision": policy_decision,
            "policy_basis": [
                "shir.v0.1.rdf_to_shir_required",
                "shir.v0.1.projection_loss_report_required",
                "shir.v0.1.semantic_leakage_detection_required",
            ],
            "decided_at": timestamp,
            "decision_ref": f"policy.decision.shir_governed_chain.{sha256_file(input_path)[:12]}",
        },
        "projection_loss_report_ref": projection_loss["report_id"],
        "semantic_leakage_checked": True,
        "outputs": [
            {
                "artifact_ref": str(path),
                "artifact_type": artifact_type,
                "hash": stage_hash(path),
            }
            for path, artifact_type in output_artifacts
        ],
        "replay": {
            "replayable": True,
            "inputs_hash": f"sha256:{sha256_file(input_path)}",
            "config_hash": CONFIG_HASH,
            "deterministic_seed": 7,
            "environment_ref": "python-stdlib-orchestrator",
        },
        "notes": "Governed SHIR chain completed: RDF/Turtle subset compiled to SHIR, projected to PyG manifest, audited for projection loss, and checked for semantic leakage.",
        "stage_receipts": {
            "rdf_to_shir": rdf_receipt["receipt_id"],
            "shir_to_pyg": pyg_receipt["receipt_id"],
            "semantic_leakage": leakage_receipt["receipt_id"],
        },
        "stage_summary": {
            "projection_loss_risk": projection_loss.get("governance", {}).get("review_status", "UNKNOWN"),
            "semantic_leakage_risk": leakage_report.get("risk_level", "UNKNOWN"),
            "semantic_leakage_markers": leakage_report.get("markers", []),
        },
    }
    return receipt


def validate_chain_receipt(schema_dir: Path, receipt_path: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise SystemExit(f"jsonschema is required for chain receipt validation: {exc}") from exc
    schema = load_json(schema_dir / "shir_receipt.schema.json")
    receipt = load_json(receipt_path)
    jsonschema.validate(instance=receipt, schema=schema)
    print(f"OK  {receipt_path}  against  shir_receipt.schema.json")


def build_error_artifact(input_path: Path, timestamp: str, error: Exception) -> Dict[str, Any]:
    return {
        "kind": "SHIRGovernedChainError",
        "created_at": timestamp,
        "compiler": {
            "name": "shir-governed-chain",
            "version": "0.1.0",
            "runtime": "python-stdlib-orchestrator",
        },
        "input_ref": str(input_path),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "policy_decision": "QUARANTINE",
        "replay": {
            "replayable": input_path.exists(),
            "config_hash": CONFIG_HASH,
        },
    }


def main() -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Run the governed SHIR demo chain end to end.")
    parser.add_argument(
        "--input",
        default=str(root / "packs" / "rdf-to-shir" / "fixtures" / "topolvm.ttl"),
        help="Input Turtle fixture",
    )
    parser.add_argument("--out-dir", required=True, help="Output directory for chain artifacts")
    parser.add_argument("--schema-dir", help="Optional semantic-serdes schemas directory")
    parser.add_argument("--timestamp", default=DEFAULT_TIMESTAMP, help="Deterministic timestamp for generated artifacts")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        rdf_dir = out_dir / "rdf-to-shir"
        pyg_dir = out_dir / "shir-to-pyg"
        leakage_dir = out_dir / "semantic-leakage"
        rdf_dir.mkdir(parents=True, exist_ok=True)
        pyg_dir.mkdir(parents=True, exist_ok=True)
        leakage_dir.mkdir(parents=True, exist_ok=True)

        run_rdf_to_shir(root, input_path, rdf_dir, args.timestamp, schema_dir)
        run_shir_to_pyg(root, rdf_dir / "assertion.json", pyg_dir, args.timestamp, schema_dir)
        run_semantic_leakage(root, pyg_dir / "pyg_manifest.json", leakage_dir, args.timestamp, schema_dir)

        receipt = build_chain_receipt(input_path, out_dir, args.timestamp, schema_dir)
        receipt_path = out_dir / "chain_run_receipt.json"
        write_json(receipt_path, receipt)
        if schema_dir:
            validate_chain_receipt(schema_dir, receipt_path)

        print(json.dumps({"out_dir": str(out_dir), "receipt": str(receipt_path), "policy_decision": receipt["policy_decision"]["decision"]}, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - orchestrator must fail closed with artifact.
        write_json(out_dir / "chain_error.json", build_error_artifact(input_path, args.timestamp, exc))
        print(f"SHIR governed chain failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
