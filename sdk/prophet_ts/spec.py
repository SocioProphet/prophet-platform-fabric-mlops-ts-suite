from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


@dataclass
class DatasetSpec:
    uri: str
    target: str
    timestamp: str = "ts"
    group: str = "sym"
    covariates: List[str] = field(default_factory=list)
    static_features: List[str] = field(default_factory=list)


@dataclass
class ModelSpec:
    family: str
    variant: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainSpec:
    engine: str  # rayjob | spark | k8sjob
    image: str
    entrypoint: Optional[str] = None
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServeSpec:
    mode: str  # online | nearline | batch | streaming
    engine: Optional[str] = None  # rayservice | kserve | seldon | none
    endpoint: Optional[str] = None
    schedule: Optional[str] = None
    sink: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalGate:
    metric: str
    op: str  # <=, >=, <, >
    value: Optional[float] = None
    baseline: Optional[str] = None


@dataclass
class EvalSpec:
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    gates: List[EvalGate] = field(default_factory=list)


@dataclass
class ProphetModelSpec:
    name: str
    owner: str
    task: str
    dataset: DatasetSpec
    model: ModelSpec
    train: TrainSpec
    serve: ServeSpec
    eval: EvalSpec = field(default_factory=EvalSpec)


def load_model_spec(path: str) -> ProphetModelSpec:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load YAML specs (pip install pyyaml).")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    md = raw.get("metadata", {})
    spec = raw.get("spec", {})

    dataset = DatasetSpec(**spec.get("dataset", {}))
    model_raw = spec.get("model", {}) or {}
    model = ModelSpec(
        family=model_raw.get("family", ""),
        variant=model_raw.get("variant"),
        params={k: v for k, v in model_raw.items() if k not in {"family", "variant"}},
    )
    train = TrainSpec(**spec.get("train", {}))
    serve = ServeSpec(**spec.get("serve", {}))

    eval_raw = spec.get("eval", {}) or {}
    gates = []
    for g in eval_raw.get("gates", []) or []:
        gates.append(EvalGate(**g))
    eval_spec = EvalSpec(metrics=eval_raw.get("metrics", []) or [], gates=gates)

    return ProphetModelSpec(
        name=md.get("name", ""),
        owner=spec.get("owner", md.get("owner", "unknown")),
        task=spec.get("task", ""),
        dataset=dataset,
        model=model,
        train=train,
        serve=serve,
        eval=eval_spec,
    )
