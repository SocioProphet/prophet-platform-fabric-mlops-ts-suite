#!/usr/bin/env python3
"""Validate decision-grade world signal MLOps pack skeletons.

This validator is intentionally dependency-free. It checks that all expected
packs exist, include README + manifest fixtures, require receipts, and declare
explicit TritFabric/Atlas alignment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"

EXPECTED_PACKS = {
    "world-signal-feature-registry",
    "fti-weather-backtest",
    "acr-graph-ml",
    "energy-ledger-calibration",
    "assessment-hitl-eval",
}

REQUIRED_TRITFABRIC_KEYS = {
    "ledger_required",
    "promotion_gate_required",
    "transport",
}

REQUIRED_REGISTRY_METHODS = {"GetLedger", "PromoteArtifact"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def validate_manifest(pack: str, manifest: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    if manifest.get("pack_id") != pack:
        errors.append(f"{path}: pack_id must be {pack}")
    if not manifest.get("version"):
        errors.append(f"{path}: version is required")
    if not manifest.get("contract_refs"):
        errors.append(f"{path}: contract_refs is required")
    if not manifest.get("inputs"):
        errors.append(f"{path}: inputs is required")
    if not manifest.get("outputs"):
        errors.append(f"{path}: outputs is required")
    if not manifest.get("gates"):
        errors.append(f"{path}: gates is required")
    if manifest.get("receipt_required") is not True:
        errors.append(f"{path}: receipt_required must be true")

    alignment = manifest.get("tritfabric_alignment")
    if not isinstance(alignment, dict):
        errors.append(f"{path}: tritfabric_alignment object is required")
        return errors

    for key in REQUIRED_TRITFABRIC_KEYS:
        if key not in alignment:
            errors.append(f"{path}: tritfabric_alignment.{key} is required")
    if alignment.get("ledger_required") is not True:
        errors.append(f"{path}: tritfabric_alignment.ledger_required must be true")
    if alignment.get("promotion_gate_required") is not True:
        errors.append(f"{path}: tritfabric_alignment.promotion_gate_required must be true")
    if "gRPC" not in str(alignment.get("transport", "")):
        errors.append(f"{path}: tritfabric_alignment.transport must declare gRPC alignment")

    registry_methods = set(alignment.get("registry_methods", []))
    missing_methods = sorted(REQUIRED_REGISTRY_METHODS - registry_methods)
    if missing_methods:
        errors.append(f"{path}: missing registry methods: {', '.join(missing_methods)}")

    gates = set(manifest.get("gates", []))
    if "tritfabric_promotion_gate" not in gates:
        errors.append(f"{path}: gates must include tritfabric_promotion_gate")
    return errors


def main() -> int:
    errors: list[str] = []
    for pack in sorted(EXPECTED_PACKS):
        root = PACKS / pack
        readme = root / "README.md"
        manifest_path = root / "fixtures" / "manifest.json"
        if not readme.exists():
            errors.append(f"missing README for pack: {pack}")
        if not manifest_path.exists():
            errors.append(f"missing manifest for pack: {pack}")
            continue
        try:
            manifest = load_json(manifest_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{manifest_path}: failed to parse JSON: {exc}")
            continue
        errors.extend(validate_manifest(pack, manifest, manifest_path))

    if errors:
        print("Decision-grade world signal MLOps pack validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(EXPECTED_PACKS)} decision-grade world signal MLOps pack(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
