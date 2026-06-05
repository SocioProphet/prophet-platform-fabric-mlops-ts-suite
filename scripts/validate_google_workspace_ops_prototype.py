#!/usr/bin/env python3
"""Validate the Google Workspace Operations Prototype scaffold.

This validator intentionally uses only the Python standard library so it can
run in lightweight agent and CI environments.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_ROOT = ROOT / "apps-script" / "google-workspace-ops-prototype"
CONTRACT_PATH = PROTOTYPE_ROOT / "fixture-contract.v0.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"missing file: {path.relative_to(ROOT)}")
    except UnicodeDecodeError as exc:
        fail(f"not valid UTF-8: {path.relative_to(ROOT)}: {exc}")


def load_contract() -> dict:
    if not CONTRACT_PATH.exists():
        fail(f"missing contract: {CONTRACT_PATH.relative_to(ROOT)}")
    try:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON contract: {exc}")


def validate_required_files(contract: dict) -> None:
    missing = []
    for relative in contract.get("required_files", []):
        path = PROTOTYPE_ROOT / relative
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    if missing:
        fail("missing required files: " + ", ".join(missing))


def validate_apps_script_functions(contract: dict) -> None:
    script_text = "\n".join(
        read_text(path)
        for path in PROTOTYPE_ROOT.glob("*.gs")
    )
    missing = []
    for function_name in contract.get("apps_script_functions", []):
        needle = f"function {function_name}("
        if needle not in script_text:
            missing.append(function_name)
    if missing:
        fail("missing Apps Script functions: " + ", ".join(missing))


def validate_config(contract: dict) -> None:
    config_path = PROTOTYPE_ROOT / "config.example.json"
    try:
        config = json.loads(read_text(config_path))
    except json.JSONDecodeError as exc:
        fail(f"invalid config.example.json: {exc}")

    missing_keys = [key for key in contract.get("required_config_keys", []) if key not in config]
    if missing_keys:
        fail("config.example.json missing keys: " + ", ".join(missing_keys))

    if config.get("dryRun") is not True:
        fail("config.example.json must default dryRun to true")

    required_fields = config.get("requiredMetadataFields", [])
    for field in contract.get("required_calendar_metadata_fields", []):
        if field not in required_fields:
            fail(f"requiredMetadataFields missing {field}")


def validate_setup_tabs(contract: dict) -> None:
    setup_text = read_text(PROTOTYPE_ROOT / "setup.gs")
    for tab in contract.get("required_sheet_tabs", []):
        if f"{tab}:" not in setup_text:
            fail(f"setup.gs missing tab definition: {tab}")


def validate_fixture_json() -> None:
    for relative in ["fixtures/calendar-event.sample.json", "fixtures/workspace-seed-rows.v0.json"]:
        path = PROTOTYPE_ROOT / relative
        try:
            json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            fail(f"invalid JSON fixture {relative}: {exc}")


def validate_fixture_csv() -> None:
    csv_text = read_text(PROTOTYPE_ROOT / "fixtures" / "dashboard-seed-rows.v0.csv")
    first_line = csv_text.splitlines()[0] if csv_text.splitlines() else ""
    expected_header = "dashboard_key,panel_key,title,source_tab,metric_definition,refresh_cadence,owner_group_id,migration_target"
    if first_line != expected_header:
        fail("dashboard seed CSV header mismatch")


def validate_safety_strings() -> None:
    sync_text = read_text(PROTOTYPE_ROOT / "sync-calendar-events-to-meetings.gs")
    required_needles = [
        "quarantined",
        "Missing required metadata",
        "writeAutomationRun_",
        "dryRun",
        "upsertByKey_",
    ]
    for needle in required_needles:
        if needle not in sync_text:
            fail(f"sync script missing safety marker: {needle}")


def main() -> None:
    contract = load_contract()
    validate_required_files(contract)
    validate_apps_script_functions(contract)
    validate_config(contract)
    validate_setup_tabs(contract)
    validate_fixture_json()
    validate_fixture_csv()
    validate_safety_strings()
    print("PASS: Google Workspace Operations Prototype scaffold is valid")
    print(f"validated_root={PROTOTYPE_ROOT.relative_to(ROOT)}")
    print(f"required_files={len(contract.get('required_files', []))}")
    print(f"required_tabs={len(contract.get('required_sheet_tabs', []))}")
    print(f"apps_script_functions={len(contract.get('apps_script_functions', []))}")


if __name__ == "__main__":
    main()
