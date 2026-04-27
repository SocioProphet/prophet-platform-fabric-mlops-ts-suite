#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for validate_michael_workflow_assets.py") from exc

from dry_run_michael_machine_science_workflow import dry_run
from render_michael_machine_science_plan import render_plan
from render_michael_machine_science_run_record import render_run_record
from render_michael_machine_science_status_transition import transition_run_record

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "workflows" / "michael_machine_science_workflowtemplate_0001.yaml"
SUBMISSION_PATH = ROOT / "workflows" / "michael_machine_science_submission_0001.yaml"
PLAN_PATH = ROOT / "examples" / "michael_machine_science_plan_0001.json"
RUN_RECORD_PATH = ROOT / "examples" / "michael_machine_science_run_record_0001.json"
STATUS_TRANSITIONS_PATH = ROOT / "examples" / "michael_machine_science_status_transitions_0001.json"
DRY_RUN_PATH = ROOT / "examples" / "michael_machine_science_dry_run_0001.json"
EXECUTION_SCHEMA_PATH = ROOT / "schemas" / "michael_workflow_execution_record.v0.1.schema.json"


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def _load_json(path: Path):
    return json.loads(path.read_text())


def _validate_status_transitions(run_record: dict, expectations: dict) -> list[dict]:
    reports = []
    for transition in expectations["transitions"]:
        target = transition["to"]
        rendered = transition_run_record(run_record, target)
        required_fields = transition.get("required_step_fields", [])
        step_reports = []
        for step in rendered["resolved_steps"]:
            missing_fields = [field for field in required_fields if field not in step]
            step_reports.append(
                {
                    "step_id": step["step_id"],
                    "status_matches": step["status"] == transition["expected_step_status"],
                    "missing_required_fields": missing_fields,
                }
            )
        reports.append(
            {
                "target_status": target,
                "status_matches": rendered["status"] == target,
                "phase_matches": rendered["lifecycle_phase"] == transition["expected_lifecycle_phase"],
                "transition_matches": rendered["transition"] == {"from": transition["from"], "to": target, "kind": "michael_machine_science_status_transition"},
                "step_reports": step_reports,
                "ok": (
                    rendered["status"] == target
                    and rendered["lifecycle_phase"] == transition["expected_lifecycle_phase"]
                    and rendered["transition"] == {"from": transition["from"], "to": target, "kind": "michael_machine_science_status_transition"}
                    and all(step_report["status_matches"] and not step_report["missing_required_fields"] for step_report in step_reports)
                ),
            }
        )
    return reports


def _validate_execution_record_shape(record: dict, schema: dict) -> dict:
    missing_required = [field for field in schema["required"] if field not in record]
    transition_statuses = [transition.get("target_status") for transition in record.get("transition_sequence", [])]
    valid_transition_statuses = all(status in {"running", "succeeded", "failed"} for status in transition_statuses)
    step_count_matches = all(
        transition.get("step_count") == len(transition.get("step_statuses", []))
        for transition in record.get("transition_sequence", [])
    )
    return {
        "missing_required": missing_required,
        "transition_statuses": transition_statuses,
        "valid_transition_statuses": valid_transition_statuses,
        "step_count_matches": step_count_matches,
        "schema_ref_matches": record.get("schema_ref") == "schemas/michael_workflow_execution_record.v0.1.schema.json",
        "ok": (
            not missing_required
            and valid_transition_statuses
            and step_count_matches
            and record.get("kind") == "michael_workflow_execution_record"
            and record.get("schema_ref") == "schemas/michael_workflow_execution_record.v0.1.schema.json"
        ),
    }


def validate_assets() -> dict:
    template_doc = _load_yaml(TEMPLATE_PATH)
    submission_doc = _load_yaml(SUBMISSION_PATH)
    stored_plan_doc = _load_json(PLAN_PATH)
    stored_run_record_doc = _load_json(RUN_RECORD_PATH)
    status_transition_expectations = _load_json(STATUS_TRANSITIONS_PATH)
    stored_dry_run_doc = _load_json(DRY_RUN_PATH)
    execution_schema_doc = _load_json(EXECUTION_SCHEMA_PATH)
    rendered_plan_doc = render_plan(template_doc, submission_doc)
    rendered_run_record_doc = render_run_record(template_doc, submission_doc)
    rendered_dry_run_doc = dry_run(stored_run_record_doc)

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

    plan_step_ids = [step["step_id"] for step in stored_plan_doc["resolved_steps"]]
    rendered_plan_step_ids = [step["step_id"] for step in rendered_plan_doc["resolved_steps"]]
    run_record_step_ids = [step["step_id"] for step in stored_run_record_doc["resolved_steps"]]
    rendered_run_record_step_ids = [step["step_id"] for step in rendered_run_record_doc["resolved_steps"]]
    task_ids = [task["name"] for task in tasks]

    plan_matches_rendered = stored_plan_doc == rendered_plan_doc
    run_record_matches_rendered = stored_run_record_doc == rendered_run_record_doc
    transition_reports = _validate_status_transitions(stored_run_record_doc, status_transition_expectations)
    transitions_ok = all(report["ok"] for report in transition_reports)
    dry_run_matches_rendered = stored_dry_run_doc == rendered_dry_run_doc
    execution_shape_report = _validate_execution_record_shape(stored_dry_run_doc, execution_schema_doc)

    return {
        "template_name": template_name,
        "submission_template_ref_matches": submission_template_ref == template_name,
        "template_parameters": template_params,
        "submission_parameters": sorted(submission_params.keys()),
        "missing_submission_parameters": sorted(set(template_params) - set(submission_params.keys())),
        "pack_refs": pack_refs,
        "missing_pack_refs": missing_pack_refs,
        "plan_step_ids": plan_step_ids,
        "rendered_plan_step_ids": rendered_plan_step_ids,
        "run_record_step_ids": run_record_step_ids,
        "rendered_run_record_step_ids": rendered_run_record_step_ids,
        "task_ids": task_ids,
        "plan_matches_task_ids": plan_step_ids == task_ids,
        "run_record_matches_task_ids": run_record_step_ids == task_ids,
        "plan_matches_rendered": plan_matches_rendered,
        "run_record_matches_rendered": run_record_matches_rendered,
        "transition_reports": transition_reports,
        "transitions_ok": transitions_ok,
        "dry_run_matches_rendered": dry_run_matches_rendered,
        "execution_shape_report": execution_shape_report,
        "ok": (
            submission_template_ref == template_name
            and not missing_pack_refs
            and not (set(template_params) - set(submission_params.keys()))
            and plan_step_ids == task_ids
            and rendered_plan_step_ids == task_ids
            and run_record_step_ids == task_ids
            and rendered_run_record_step_ids == task_ids
            and plan_matches_rendered
            and run_record_matches_rendered
            and transitions_ok
            and dry_run_matches_rendered
            and execution_shape_report["ok"]
        ),
    }


def main() -> int:
    report = validate_assets()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
