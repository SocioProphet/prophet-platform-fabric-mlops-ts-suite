#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for render_michael_machine_science_run_record.py") from exc

from render_michael_machine_science_plan import render_plan


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def render_run_record(template_doc: dict, submission_doc: dict) -> dict:
    plan = render_plan(template_doc, submission_doc)

    artifact_map = {
        "belief-update": ["belief_state", "weighted_rule_set", "hypothesis[]"],
        "belief-promotion-gate": ["promotion_decision"],
        "candidate-law-discovery": ["equation_candidate[]", "counterexample[]", "evidence_packet"],
        "candidate-law-promotion-gate": ["promotion_decision"],
        "human-twin-boundary-gate": ["boundary_decision"],
    }

    resolved_steps = []
    for step in plan["resolved_steps"]:
        resolved_steps.append(
            {
                **step,
                "status": "planned",
                "expected_artifacts": artifact_map.get(step["step_id"], []),
            }
        )

    return {
        "run_id": "michael-machine-science-run-0001",
        "workflow_template": plan["workflow_template"],
        "submission_name_prefix": plan["submission_name_prefix"],
        "parameters": plan["parameters"],
        "status": "planned",
        "lifecycle_phase": "pre-execution",
        "step_count": len(resolved_steps),
        "resolved_steps": resolved_steps,
        "artifact_expectations": {
            "benchmark_report": "artifact://benchmark/report/pending",
            "promotion_decisions": [
                "promotion_decision://belief-promotion-gate",
                "promotion_decision://candidate-law-promotion-gate",
            ],
            "rollback_record": "rollback_record://pending",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: render_michael_machine_science_run_record.py <workflowtemplate.yaml> <workflow.yaml>",
            file=sys.stderr,
        )
        return 2

    template_doc = _load_yaml(Path(argv[1]))
    submission_doc = _load_yaml(Path(argv[2]))
    run_record = render_run_record(template_doc, submission_doc)
    print(json.dumps(run_record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
