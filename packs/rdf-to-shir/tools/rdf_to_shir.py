#!/usr/bin/env python3
"""Compile a deterministic RDF/Turtle subset into SHIR JSON artifacts.

This pack is intentionally narrow for v0.1. It proves the runtime contract
without introducing a heavy RDF or graph-ML dependency. Later versions may
replace the parser with rdflib while preserving the same SHIR outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PREFIX_RE = re.compile(r"^@prefix\s+([A-Za-z][\w-]*):\s*<([^>]+)>\s*\.\s*$")
TRIPLE_RE = re.compile(r"^(\S+)\s+(\S+)\s+(.+?)\s*\.\s*$")

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
CONFIG_HASH = "sha256:rdf-to-shir-pack-v0.1-default"

LABEL_PREDICATES = {
    "http://www.w3.org/2000/01/rdf-schema#label",
    "https://schema.org/name",
}

TYPE_HINTS = {
    "TopoLVM": "Technology",
    "PersistentVolume": "StorageResource",
    "KubernetesNode": "ComputeNode",
    "AgentMachineNode": "ComputeNode",
    "LocalStorage": "StorageResource",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def local_name(iri: str) -> str:
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rstrip("/").rsplit("/", 1)[-1]


def stable_id(prefix: str, *parts: str) -> str:
    cleaned: List[str] = []
    for part in parts:
        token = re.sub(r"[^A-Za-z0-9]+", "_", local_name(part)).strip("_").lower()
        if token:
            cleaned.append(token)
    return ".".join([prefix, *cleaned])


def strip_turtle_comment(line: str) -> str:
    """Strip comments while preserving # inside IRIs and string literals."""
    in_angle = False
    in_quote = False
    escaped = False
    for idx, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_quote:
            escaped = True
            continue
        if char == '"' and not in_angle:
            in_quote = not in_quote
            continue
        if char == "<" and not in_quote:
            in_angle = True
            continue
        if char == ">" and in_angle and not in_quote:
            in_angle = False
            continue
        if char == "#" and not in_angle and not in_quote:
            return line[:idx]
    return line


def expand_term(term: str, prefixes: Dict[str, str]) -> str:
    if term.startswith("<") and term.endswith(">"):
        return term[1:-1]
    if ":" in term:
        prefix, suffix = term.split(":", 1)
        if prefix in prefixes:
            return prefixes[prefix] + suffix
    raise ValueError(f"cannot expand term {term!r}; missing prefix or unsupported syntax")


def expand_object(raw: str, prefixes: Dict[str, str]) -> Dict[str, Any]:
    raw = raw.strip()
    if raw.startswith('"'):
        end = raw.rfind('"')
        if end <= 0:
            raise ValueError(f"unterminated literal object {raw!r}")
        return {"kind": "literal", "value": raw[1:end]}
    return {"kind": "iri", "iri": expand_term(raw, prefixes)}


def parse_turtle_subset(text: str) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    prefixes: Dict[str, str] = {}
    triples: List[Dict[str, Any]] = []
    logical_lines: List[str] = []

    for raw_line in text.splitlines():
        line = strip_turtle_comment(raw_line).strip()
        if line:
            logical_lines.append(line)

    for line_number, line in enumerate(logical_lines, start=1):
        prefix_match = PREFIX_RE.match(line)
        if prefix_match:
            prefixes[prefix_match.group(1)] = prefix_match.group(2)
            continue

        triple_match = TRIPLE_RE.match(line)
        if not triple_match:
            raise ValueError(f"unsupported Turtle subset at logical line {line_number}: {line}")

        subj, pred, obj_raw = triple_match.groups()
        triples.append(
            {
                "line_number": line_number,
                "subject": expand_term(subj, prefixes),
                "predicate": expand_term(pred, prefixes),
                "object": expand_object(obj_raw, prefixes),
                "raw": line,
            }
        )

    return prefixes, triples


def collect_labels(triples: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for triple in triples:
        if triple["predicate"] in LABEL_PREDICATES and triple["object"]["kind"] == "literal":
            labels[triple["subject"]] = triple["object"]["value"]
    return labels


def term_payload(iri: str, labels: Dict[str, str]) -> Dict[str, str]:
    label = labels.get(iri, local_name(iri))
    return {
        "id": stable_id("entity", label),
        "label": label,
        "type": TYPE_HINTS.get(label, "Resource"),
        "iri": iri,
    }


def predicate_payload(iri: str) -> Dict[str, str]:
    label = local_name(iri)
    return {"id": stable_id("relation", label), "label": label, "iri": iri}


def find_primary_relation(triples: List[Dict[str, Any]]) -> Dict[str, Any]:
    relations = [
        triple
        for triple in triples
        if triple["predicate"] not in LABEL_PREDICATES and triple["object"]["kind"] == "iri"
    ]
    if not relations:
        raise ValueError("no object-property triples found for SHIR candidate assertion")
    for triple in relations:
        if local_name(triple["predicate"]).lower() == "provisions":
            return triple
    return relations[0]


def find_target_context(primary: Dict[str, Any], triples: List[Dict[str, Any]]) -> Optional[str]:
    for triple in triples:
        if triple["subject"] == primary["subject"] and local_name(triple["predicate"]).lower() in {
            "targetcontext",
            "scopedto",
            "context",
        }:
            if triple["object"]["kind"] == "iri":
                return triple["object"]["iri"]
    return None


def evidence_anchor(input_ref: str, source_hash: str, triple: Dict[str, Any]) -> Dict[str, Any]:
    anchor_hash = sha256_text(triple["raw"] + source_hash)[:16]
    return {
        "anchor_id": f"anchor.rdf.{anchor_hash}",
        "anchor_type": "RDF_TRIPLE",
        "artifact_ref": input_ref,
        "selector": {
            "logical_line": triple["line_number"],
            "triple": triple["raw"],
            "subject": triple["subject"],
            "predicate": triple["predicate"],
            "object": triple["object"],
        },
    }


def build_candidate(
    primary: Dict[str, Any],
    labels: Dict[str, str],
    input_ref: str,
    source_hash: str,
    timestamp: str,
) -> Dict[str, Any]:
    subj = primary["subject"]
    pred = primary["predicate"]
    obj = primary["object"]["iri"]
    return {
        "assertion_id": stable_id("shir.candidate", subj, pred, obj),
        "kind": "CandidateAssertion",
        "candidate_status": "EXTRACTED",
        "plane": "DERIVED",
        "truth_class": "INFERRED",
        "time_model": "SNAPSHOT",
        "source": {
            "source_type": "RDF_TRIPLE",
            "source_ref": input_ref,
            "source_hash": f"sha256:{source_hash}",
            "snapshot_ref": f"snapshot://rdf-to-shir/{source_hash[:12]}",
        },
        "subject": term_payload(subj, labels),
        "predicate": predicate_payload(pred),
        "object": term_payload(obj, labels),
        "evidence_anchors": [evidence_anchor(input_ref, source_hash, primary)],
        "induction_trace": {
            "extractor_id": "rdf-to-shir-pack.v0.1",
            "method": "RDF_PARSE",
            "run_id": f"run.rdf-to-shir.{source_hash[:12]}",
            "created_at": timestamp,
        },
        "confidence": 1.0,
        "governance": {
            "admissibility_tier": "RAW",
            "review_status": "REQUIRED",
            "policy_basis": ["shir.v0.1.rdf_parse_candidate_requires_validation"],
        },
        "leakage_markers": ["NONE"],
        "replay": {
            "inputs_hash": f"sha256:{source_hash}",
            "config_hash": CONFIG_HASH,
            "replayable": True,
            "deterministic_seed": 7,
        },
        "notes": "Generated by deterministic RDF/Turtle subset compiler; candidate must pass ontology validation before promotion.",
    }


def build_assertion(
    primary: Dict[str, Any],
    target_context_iri: Optional[str],
    labels: Dict[str, str],
    input_ref: str,
    source_hash: str,
    timestamp: str,
    receipt_id: str,
) -> Dict[str, Any]:
    subj = primary["subject"]
    pred = primary["predicate"]
    obj = primary["object"]["iri"]
    pred_label = local_name(pred)
    context_iri = target_context_iri or obj
    context_term = term_payload(context_iri, labels)
    subject_term = term_payload(subj, labels)
    object_term = term_payload(obj, labels)

    return {
        "assertion_id": stable_id("shir.assertion", subj, pred, obj),
        "kind": "Assertion",
        "assertion_status": "VALIDATED",
        "plane": "ENTITY",
        "truth_class": "ASSERTED",
        "time_model": "SNAPSHOT",
        "connector": {
            "connector_id": stable_id("connector", pred_label, "resource", "context"),
            "label": f"{pred_label}(provider, resource, target_context)",
            "iri": pred,
            "roles": ["provider", "resource", "target_context"],
        },
        "role_bindings": [
            {
                "role": "provider",
                "participant_id": subject_term["id"],
                "participant_type": "NODE",
                "label": subject_term["label"],
            },
            {
                "role": "resource",
                "participant_id": object_term["id"],
                "participant_type": "NODE",
                "label": object_term["label"],
            },
            {
                "role": "target_context",
                "participant_id": context_term["id"],
                "participant_type": "NODE",
                "label": context_term["label"],
            },
        ],
        "context": {
            "context_id": stable_id("context", "rdf", source_hash[:12]),
            "label": "RDF-to-SHIR compiled graph context",
            "scope": "DOMAIN",
            "parent_context_refs": ["context.shir.rdf_to_shir_pack"],
        },
        "temporal_scope": {
            "time_model": "SNAPSHOT",
            "observed_at": timestamp,
            "transaction_time": timestamp,
        },
        "policy_scope": {
            "policy_scope_id": "policy.scope.public.technical-docs",
            "classification": "PUBLIC",
            "export_eligible": True,
            "training_eligible": True,
            "policy_basis": ["policy.public_technical_docs.allowed_for_training"],
        },
        "evidence_anchors": [evidence_anchor(input_ref, source_hash, primary)],
        "governance": {
            "admissibility_tier": "VALIDATED",
            "review_status": "APPROVED",
            "policy_basis": ["shir.v0.1.rdf_parse_validated_assertion_fixture"],
        },
        "receipt_ref": receipt_id,
        "source_candidate_refs": [stable_id("shir.candidate", subj, pred, obj)],
        "noise_assessments": [],
    }


def build_receipt(
    candidate: Dict[str, Any],
    assertion: Dict[str, Any],
    input_ref: str,
    source_hash: str,
    timestamp: str,
    out_dir_ref: str,
    receipt_id: str,
) -> Dict[str, Any]:
    candidate_hash = sha256_text(json.dumps(candidate, sort_keys=True))
    assertion_hash = sha256_text(json.dumps(assertion, sort_keys=True))
    return {
        "receipt_id": receipt_id,
        "kind": "Receipt",
        "receipt_type": "INDUCTION",
        "created_at": timestamp,
        "compiler": {
            "name": "rdf-to-shir-pack",
            "version": "0.1.0",
            "commit_sha": "unreleased-pack-v0.1",
            "runtime": "python-stdlib",
        },
        "ontology_profile": {
            "profile_id": "ontogenesis.shir.v0.1",
            "version": "0.1.0-draft",
            "module_refs": ["https://github.com/SocioProphet/ontogenesis/blob/main/docs/specs/shir-v0.1.md"],
            "shape_refs": ["shapes://pending/shir-core"],
        },
        "source_hashes": [
            {"algorithm": "sha256", "value": source_hash, "artifact_ref": input_ref}
        ],
        "transform": {
            "transform_id": "transform.rdf.to.shir.v0.1",
            "transform_type": "RDF_TO_SHIR",
            "config_hash": CONFIG_HASH,
            "parameters": {
                "parser": "turtle-subset",
                "skolemize_blank_nodes": False,
                "emit_candidate_assertion": True,
                "emit_assertion_fixture": True,
            },
        },
        "policy_decision": {
            "decision": "ALLOW",
            "policy_basis": ["policy.public_technical_docs.allowed_for_training"],
            "decided_at": timestamp,
            "decision_ref": f"policy.decision.rdf-to-shir.{source_hash[:12]}",
        },
        "semantic_leakage_checked": False,
        "outputs": [
            {
                "artifact_ref": f"{out_dir_ref}/candidate_assertion.json",
                "artifact_type": "SHIR_JSON",
                "hash": {
                    "algorithm": "sha256",
                    "value": candidate_hash,
                    "artifact_ref": f"{out_dir_ref}/candidate_assertion.json",
                },
            },
            {
                "artifact_ref": f"{out_dir_ref}/assertion.json",
                "artifact_type": "SHIR_JSON",
                "hash": {
                    "algorithm": "sha256",
                    "value": assertion_hash,
                    "artifact_ref": f"{out_dir_ref}/assertion.json",
                },
            },
        ],
        "replay": {
            "replayable": True,
            "inputs_hash": f"sha256:{source_hash}",
            "config_hash": CONFIG_HASH,
            "deterministic_seed": 7,
            "environment_ref": "python-stdlib",
        },
        "notes": "Receipt binds deterministic RDF-to-SHIR output artifacts to source hash and compiler configuration.",
    }


def build_error_artifact(
    input_ref: str,
    source_hash: Optional[str],
    timestamp: str,
    error: Exception,
) -> Dict[str, Any]:
    return {
        "kind": "RDFToSHIRCompileError",
        "created_at": timestamp,
        "compiler": {
            "name": "rdf-to-shir-pack",
            "version": "0.1.0",
            "runtime": "python-stdlib",
        },
        "input_ref": input_ref,
        "source_hash": f"sha256:{source_hash}" if source_hash else None,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "policy_decision": "QUARANTINE",
        "replay": {
            "replayable": bool(source_hash),
            "inputs_hash": f"sha256:{source_hash}" if source_hash else None,
            "config_hash": CONFIG_HASH,
        },
    }


def write_json(path: Path, doc: Dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_outputs(schema_dir: Path, out_dir: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise SystemExit(f"jsonschema is required for --schema-dir validation: {exc}") from exc

    pairs = [
        ("shir_candidate_assertion.schema.json", "candidate_assertion.json"),
        ("shir_assertion.schema.json", "assertion.json"),
        ("shir_receipt.schema.json", "receipt.json"),
    ]
    for schema_name, output_name in pairs:
        schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
        instance = json.loads((out_dir / output_name).read_text(encoding="utf-8"))
        jsonschema.validate(instance=instance, schema=schema)
        print(f"OK  {output_name}  against  {schema_name}")


def compile_file(input_path: Path, out_dir: Path, timestamp: str, schema_dir: Optional[Path]) -> Dict[str, str]:
    text = input_path.read_text(encoding="utf-8")
    source_hash = sha256_text(text)
    input_ref = str(input_path)

    _, triples = parse_turtle_subset(text)
    labels = collect_labels(triples)
    primary = find_primary_relation(triples)
    target_context_iri = find_target_context(primary, triples)
    receipt_id = f"shir.receipt.rdf_to_shir.{source_hash[:12]}"

    candidate = build_candidate(primary, labels, input_ref, source_hash, timestamp)
    assertion = build_assertion(primary, target_context_iri, labels, input_ref, source_hash, timestamp, receipt_id)
    receipt = build_receipt(candidate, assertion, input_ref, source_hash, timestamp, str(out_dir), receipt_id)

    write_json(out_dir / "candidate_assertion.json", candidate)
    write_json(out_dir / "assertion.json", assertion)
    write_json(out_dir / "receipt.json", receipt)

    if schema_dir:
        validate_outputs(schema_dir, out_dir)

    return {"out_dir": str(out_dir), "source_hash": source_hash, "receipt_id": receipt_id}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a deterministic RDF/Turtle subset into SHIR JSON artifacts.")
    parser.add_argument("--input", required=True, help="Input Turtle file")
    parser.add_argument("--out-dir", required=True, help="Output directory for SHIR JSON artifacts")
    parser.add_argument("--schema-dir", help="Optional semantic-serdes schema directory for validation")
    parser.add_argument(
        "--timestamp",
        default=DEFAULT_TIMESTAMP,
        help="Deterministic timestamp used in emitted artifacts; default is stable for reproducible tests.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    schema_dir = Path(args.schema_dir) if args.schema_dir else None

    source_hash: Optional[str] = None
    try:
        if input_path.exists():
            source_hash = sha256_text(input_path.read_text(encoding="utf-8"))
        result = compile_file(input_path, out_dir, args.timestamp, schema_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must emit quarantine artifact for any compile failure.
        error_artifact = build_error_artifact(str(input_path), source_hash, args.timestamp, exc)
        write_json(out_dir / "compile_error.json", error_artifact)
        print(f"rdf-to-shir compile failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
