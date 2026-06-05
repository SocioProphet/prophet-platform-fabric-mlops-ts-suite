#!/usr/bin/env python3
"""Validate an OpenTofu/Terraform plan JSON against the default Workspace mesh safety contract.

Usage:
  python3 scripts/validate_workspace_mesh_plan_json.py \
    infra/google-workspace-ops-mesh/generated/default-plan.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "infra" / "google-workspace-ops-mesh" / "plan-safety.v0.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON {path}: {exc}")


def normalize_address(change: dict) -> str:
    address = change.get("address", "")
    if address:
        return address
    return change.get("name", "")


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        fail("usage: validate_workspace_mesh_plan_json.py <plan-json-path>")

    plan_path = Path(argv[1]).resolve()
    contract = load_json(CONTRACT_PATH)
    plan = load_json(plan_path)

    allowed_types = set(contract.get("allowed_resource_types", []))
    allowed_actions = {tuple(actions) for actions in contract.get("allowed_actions", [])}
    forbidden_prefixes = tuple(contract.get("forbidden_resource_type_prefixes", []))
    expected_resources = set(contract.get("expected_default_resources", []))

    resource_changes = plan.get("resource_changes", [])
    actionable_changes = []

    for change in resource_changes:
        resource_type = change.get("type", "")
        address = normalize_address(change)
        actions = tuple(change.get("change", {}).get("actions", []))

        if actions == ("no-op",):
            continue

        actionable_changes.append(change)

        if resource_type.startswith(forbidden_prefixes):
            fail(f"forbidden resource type in default plan: {resource_type} at {address}")

        if resource_type not in allowed_types:
            fail(f"resource type not allowed in default plan: {resource_type} at {address}")

        if actions not in allowed_actions:
            fail(f"action not allowed for {address}: {actions}")

    actionable_addresses = {normalize_address(change) for change in actionable_changes}
    missing_expected = expected_resources - actionable_addresses
    unexpected = actionable_addresses - expected_resources

    if missing_expected:
        fail("default plan missing expected local resources: " + ", ".join(sorted(missing_expected)))

    if unexpected:
        fail("default plan contains unexpected resources: " + ", ".join(sorted(unexpected)))

    expected_count = contract.get("expected_default_resource_count")
    if expected_count is not None and len(actionable_changes) != expected_count:
        fail(f"expected {expected_count} actionable changes, found {len(actionable_changes)}")

    print("PASS: Workspace mesh default plan is local-file-only")
    print(f"plan_json={plan_path}")
    print(f"actionable_changes={len(actionable_changes)}")


if __name__ == "__main__":
    main(sys.argv)
