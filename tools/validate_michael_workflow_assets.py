#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for validate_michael_workflow_assets.py") from exc

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "workflows" / "michael_machine_science_workflowtemplate_0001.yaml"
SUBMISSION_PATH = ROOT / "workflows" / "michael_machine_science_submission_0001.yaml"
PLAN_PATH = ROOT / "examples" / "michael_machine_science_plan_0001.json"


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def _load_json(path: Path):
    return json.loads(path.read_text())


def validate_assets() -> dict:
    template_doc = _load_yaml(TEMPLATE_PATH)
    submission_doc = _load_yaml(SUBMISSION_PATH)
    plan_doc = _load_json(PLAN_PATH)

    template_name = template_doc["metadata"]["name"]
    submission_template_ref = submission_doc["spec"]["workflowTemplateRef"]["name"]
    submission_params = {
        item["name"]: item.get("value", "")
        for item in submission_doc["spec"]["arguments"]["parameters"]
    }
    template_params = [p["name"] for p in template_doc["spec"]["arguments"]["parameters"]]

    entrypoint_name = template_doc["spec"]["entrypoint"]
    entrypoint = next(t for t in template_doc["spec"]["templates"] if t["name"] == entrypoint_name)
    tasks = entrypoint["dag"]["tasks"]
    pack_refs = [
        next(p["value"] for p in task["arguments"]["parameters"] if p["name"] == "pack_ref")
        for task in tasks
    ]

    missing_pack_refs = [ref for ref in pack_refs if not (ROOT / ref).exists()]

    plan_step_ids = [step["step_id"] for step in plan_doc["resolved_steps"]]
    task_ids = [task["name"] for task in tasks]

    return {
        "template_name": template_name,
        "submission_template_ref_matches": submission_template_ref == template_name,
        "template_parameters": template_params,
        "submission_parameters": sorted(submission_params.keys()),
        "missing_submission_parameters": sorted(set(template_params) - set(submission_params.keys())),
        "pack_refs": pack_refs,
        "missing_pack_refs": missing_pack_refs,
        "plan_step_ids": plan_step_ids,
        "task_ids": task_ids,
        "plan_matches_task_ids": plan_step_ids == task_ids,
        "ok": (
            submission_template_ref == template_name
            and not missing_pack_refs
            and not (set(template_params) - set(submission_params.keys()))
            and plan_step_ids == task_ids
        ),
    }


def main() -> int:
    report = validate_assets()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
