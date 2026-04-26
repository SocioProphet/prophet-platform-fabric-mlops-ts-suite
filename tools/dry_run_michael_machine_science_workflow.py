#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from render_michael_machine_science_status_transition import transition_run_record

SCHEMA_REF = "schemas/michael_workflow_execution_record.v0.1.schema.json"


def _load_json(path: Path):
    return json.loads(path.read_text())


def _summarize_transition(record: dict) -> dict:
    return {
        "target_status": record["status"],
        "lifecycle_phase": record["lifecycle_phase"],
        "transition": record["transition"],
        "step_count": len(record["resolved_steps"]),
        "step_statuses": [
            {
                "step_id": step["step_id"],
                "status": step["status"],
                "expected_artifacts": step.get("expected_artifacts", []),
                "evidence_refs": step.get("evidence_refs", []),
                "failure_evidence_ref": step.get("failure_evidence_ref"),
            }
            for step in record["resolved_steps"]
        ],
    }


def dry_run(run_record: dict) -> dict:
    transitions = [
        transition_run_record(run_record, "running"),
        transition_run_record(run_record, "succeeded"),
        transition_run_record(run_record, "failed"),
    ]

    return {
        "kind": "michael_workflow_execution_record",
        "schema_ref": SCHEMA_REF,
        "execution_record_id": "michael-machine-science-dry-run-0001",
        "source_run_id": run_record["run_id"],
        "workflow_template": run_record["workflow_template"],
        "mode": "local-dry-run",
        "transition_sequence": [_summarize_transition(record) for record in transitions],
        "summary": {
            "transition_count": 3,
            "final_nominal_status": "succeeded",
            "failure_branch_present": True,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: dry_run_michael_machine_science_workflow.py <run_record.json>", file=sys.stderr)
        return 2

    run_record = _load_json(Path(argv[1]))
    print(json.dumps(dry_run(run_record), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
