#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for render_michael_machine_science_plan.py") from exc

PARAM_RE = re.compile(r"\{\{inputs\.parameters\.([A-Za-z0-9_\-]+)\}\}")


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def _replace_params(text: str, params: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(params.get(key, match.group(0)))
    return PARAM_RE.sub(repl, text)


def _find_template_obj(doc: dict, template_name: str) -> dict:
    for template in doc["spec"]["templates"]:
        if template.get("name") == template_name:
            return template
    raise KeyError(f"template not found: {template_name}")


def render_plan(template_doc: dict, submission_doc: dict) -> dict:
    params = {
        item["name"]: item.get("value", "")
        for item in submission_doc["spec"]["arguments"]["parameters"]
    }

    entrypoint_name = template_doc["spec"]["entrypoint"]
    entrypoint = _find_template_obj(template_doc, entrypoint_name)
    tasks = entrypoint["dag"]["tasks"]

    resolved_steps = []
    for task in tasks:
        args = {
            p["name"]: _replace_params(str(p.get("value", "")), params)
            for p in task.get("arguments", {}).get("parameters", [])
        }
        resolved_steps.append(
            {
                "step_id": task["name"],
                "template": task["template"],
                "dependencies": task.get("dependencies", []),
                "pack_ref": args.get("pack_ref"),
                "context_json": args.get("context_json"),
            }
        )

    return {
        "workflow_template": template_doc["metadata"]["name"],
        "submission_name_prefix": submission_doc["metadata"].get("generateName"),
        "parameters": params,
        "resolved_steps": resolved_steps,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: render_michael_machine_science_plan.py <workflowtemplate.yaml> <workflow.yaml>",
            file=sys.stderr,
        )
        return 2

    template_doc = _load_yaml(Path(argv[1]))
    submission_doc = _load_yaml(Path(argv[2]))
    plan = render_plan(template_doc, submission_doc)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
