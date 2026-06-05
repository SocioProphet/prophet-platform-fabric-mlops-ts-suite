#!/usr/bin/env python3
"""Validate the Google Workspace Operations Mesh scaffold.

This validator checks repository structure and safety defaults without running
Terraform or contacting Google APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESH_ROOT = ROOT / "infra" / "google-workspace-ops-mesh"

REQUIRED_FILES = [
    "README.md",
    "versions.tf",
    "providers.tf",
    "variables.tf",
    "locals.tf",
    "main.tf",
    "outputs.tf",
    "terraform.tfvars.example",
]

SAFETY_NEEDLES = {
    "variables.tf": [
        'variable "enable_google_project_services"',
        'default     = false',
        'variable "enable_workspace_groups"',
        'variable "prototype_dry_run"',
        'default     = true',
        'variable "generate_local_deployment_files"',
    ],
    "main.tf": [
        "var.enable_google_project_services ?",
        "var.enable_workspace_groups ?",
        "var.generate_local_deployment_files ?",
        "local_file",
    ],
    "README.md": [
        "apply-safe by default",
        "does not create groups",
        "Deployment boundary",
    ],
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read_text(relative: str) -> str:
    path = MESH_ROOT / relative
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        fail(f"not valid UTF-8: {path.relative_to(ROOT)}: {exc}")


def validate_required_files() -> None:
    missing = [name for name in REQUIRED_FILES if not (MESH_ROOT / name).exists()]
    if missing:
        fail("missing Terraform mesh files: " + ", ".join(missing))


def validate_safety_needles() -> None:
    for relative, needles in SAFETY_NEEDLES.items():
        text = read_text(relative)
        for needle in needles:
            if needle not in text:
                fail(f"{relative} missing safety marker: {needle}")


def validate_no_obvious_secrets() -> None:
    forbidden = [
        "-----BEGIN PRIVATE KEY-----",
        "client_secret",
        "refresh_token",
        "access_token",
    ]
    for path in MESH_ROOT.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in forbidden:
                if marker in text:
                    fail(f"possible secret marker {marker} in {path.relative_to(ROOT)}")


def main() -> None:
    validate_required_files()
    validate_safety_needles()
    validate_no_obvious_secrets()
    print("PASS: Google Workspace Operations Terraform mesh scaffold is valid")
    print(f"validated_root={MESH_ROOT.relative_to(ROOT)}")
    print(f"required_files={len(REQUIRED_FILES)}")


if __name__ == "__main__":
    main()
