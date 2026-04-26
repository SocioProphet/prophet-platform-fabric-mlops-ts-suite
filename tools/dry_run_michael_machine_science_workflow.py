#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from render_michael_machine_science_status_transition import transition_run_record


def _load_json(path: Path):
    return json.loads(path.read_text())


def dry_run(run_record: dict) -> dict:
    running = transition_run_record(run_record, "running")
    succeeded = transition_run_record(run_record, "succeeded")
    failed = transition_run_record(run_record, "failed")

    return {
        "dry_run_id": "michael-machine-science-dry-run-0001",
        "source_run_id": run_record["run_id"],
        "mode": "local-dry-run",
        "transition_sequence": [
            {
                "target_status": "running",
                "record": running,
            },
            {
                "target_status": "succeeded",
                "record": succeeded,
            },
            {
                "target_status": "failed",
                "record": failed,
            },
        ],
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
