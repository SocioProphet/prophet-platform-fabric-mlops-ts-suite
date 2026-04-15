from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .spec import EvalGate, load_model_spec


def _compare(op: str, left: float, right: float) -> bool:
    if op == "<=":
        return left <= right
    if op == "<":
        return left < right
    if op == ">=":
        return left >= right
    if op == ">":
        return left > right
    raise ValueError(f"Unsupported gate op: {op}")


def apply_gates(metrics: Dict[str, Any], gates: List[EvalGate]) -> Tuple[bool, List[Dict[str, Any]]]:
    """Apply metric gates. Baseline comparisons are not implemented (requires registry lookup)."""
    details: List[Dict[str, Any]] = []
    passed = True
    for g in gates:
        mval = metrics.get(g.metric)
        ok = False
        reason = ""
        if mval is None:
            ok = False
            reason = "metric_missing"
        elif g.value is not None:
            ok = _compare(g.op, float(mval), float(g.value))
            reason = "ok" if ok else "threshold_failed"
        elif g.baseline is not None:
            ok = False
            reason = "baseline_gate_not_implemented"
        else:
            ok = False
            reason = "invalid_gate"
        details.append(
            {
                "metric": g.metric,
                "op": g.op,
                "value": g.value,
                "baseline": g.baseline,
                "observed": mval,
                "passed": ok,
                "reason": reason,
            }
        )
        passed = passed and ok
    return passed, details


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True, help="Path to ProphetModelSpec YAML")
    p.add_argument("--metrics", required=True, help="Path to metrics.json produced by training")
    p.add_argument("--out", required=True, help="Output path for gate result JSON")
    args = p.parse_args()

    spec = load_model_spec(args.spec)
    metrics = json.loads(Path(args.metrics).read_text())

    passed, details = apply_gates(metrics, spec.eval.gates)

    out = {
        "passed": passed,
        "details": details,
        "model_name": spec.name,
        "task": spec.task,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

    # Argo-friendly: also print a single token line
    print("GATES_PASSED=", "true" if passed else "false")


if __name__ == "__main__":
    main()
