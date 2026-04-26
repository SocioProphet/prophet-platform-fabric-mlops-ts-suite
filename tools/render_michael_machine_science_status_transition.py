#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

VALID_TARGETS = {"running", "succeeded", "failed"}


def _load_json(path: Path):
    return json.loads(path.read_text())


def transition_run_record(run_record: dict, target_status: str) -> dict:
    if target_status not in VALID_TARGETS:
        raise ValueError(f"target_status must be one of {sorted(VALID_TARGETS)}")

    transitioned = copy.deepcopy(run_record)
    transitioned["status"] = target_status
    transitioned["lifecycle_phase"] = {
        "running": "execution",
        "succeeded": "post-execution",
        "failed": "post-execution",
    }[target_status]

    for step in transitioned["resolved_steps"]:
        step["status"] = target_status if target_status != "failed" else "failed"
        if target_status == "running":
            step["started_at_ref"] = f"time://{step['step_id']}/started"
        elif target_status == "succeeded":
            step["completed_at_ref"] = f"time://{step['step_id']}/completed"
            step["evidence_refs"] = [f"evidence://{step['step_id']}/receipt"]
        elif target_status == "failed":
            step["failed_at_ref"] = f"time://{step['step_id']}/failed"
            step["failure_evidence_ref"] = f"evidence://{step['step_id']}/failure"

    transitioned["transition"] = {
        "from": run_record.get("status", "planned"),
        "to": target_status,
        "kind": "michael_machine_science_status_transition",
    }
    return transitioned


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: render_michael_machine_science_status_transition.py <run_record.json> <running|succeeded|failed>",
            file=sys.stderr,
        )
        return 2

    run_record = _load_json(Path(argv[1]))
    transitioned = transition_run_record(run_record, argv[2])
    print(json.dumps(transitioned, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
