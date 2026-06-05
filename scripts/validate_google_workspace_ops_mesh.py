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
OPTIONAL_GROUPS_ROOT = MESH_ROOT / "optional-workspace-groups"

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

OPTIONAL_GROUPS_REQUIRED_FILES = [
    "README.md",
    "versions.tf",
    "providers.tf",
    "variables.tf",
    "main.tf",
    "outputs.tf",
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
        "var.generate_local_deployment_files ?",
        "local_file",
    ],
    "README.md": [
        "apply-safe by default",
        "does not create groups",
        "Deployment boundary",
        "OpenTofu-first",
    ],
}

FORBIDDEN_DEFAULT_ROOT_NEEDLES = [
    'provider "googleworkspace"',
    'resource "googleworkspace_group"',
    'resource "googleworkspace_group_member"',
]

SECRET_SCAN_EXCLUDED_DIR_NAMES = {
    ".terraform",
    "generated",
    ".git",
    "node_modules",
}

SECRET_SCAN_SUFFIX_ALLOWLIST = {
    ".md",
    ".tf",
    ".tfvars.example",
    ".py",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read_text(relative: str, root: Path = MESH_ROOT) -> str:
    path = root / relative
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


def validate_optional_groups_root() -> None:
    missing = [name for name in OPTIONAL_GROUPS_REQUIRED_FILES if not (OPTIONAL_GROUPS_ROOT / name).exists()]
    if missing:
        fail("missing optional Workspace groups files: " + ", ".join(missing))
    provider_text = read_text("providers.tf", OPTIONAL_GROUPS_ROOT)
    if 'provider "googleworkspace"' not in provider_text:
        fail("optional Workspace groups root missing googleworkspace provider")
    variables_text = read_text("variables.tf", OPTIONAL_GROUPS_ROOT)
    for needle in ['variable "google_workspace_customer_id"', 'variable "workspace_groups"']:
        if needle not in variables_text:
            fail(f"optional Workspace groups variables missing {needle}")


def validate_safety_needles() -> None:
    for relative, needles in SAFETY_NEEDLES.items():
        text = read_text(relative)
        for needle in needles:
            if needle not in text:
                fail(f"{relative} missing safety marker: {needle}")


def validate_default_root_has_no_workspace_provider() -> None:
    for path in [MESH_ROOT / "providers.tf", MESH_ROOT / "main.tf", MESH_ROOT / "versions.tf"]:
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_DEFAULT_ROOT_NEEDLES:
            if needle in text:
                fail(f"default mesh root must not contain {needle} in {path.relative_to(ROOT)}")


def should_scan_for_secrets(path: Path) -> bool:
    relative = path.relative_to(MESH_ROOT)
    if any(part in SECRET_SCAN_EXCLUDED_DIR_NAMES for part in relative.parts):
        return False
    if path.name == ".terraform.lock.hcl":
        return True
    return any(str(path).endswith(suffix) for suffix in SECRET_SCAN_SUFFIX_ALLOWLIST)


def validate_no_obvious_secrets() -> None:
    forbidden = [
        "-----BEGIN PRIVATE KEY-----",
        "client_secret",
        "refresh_token",
        "access_token",
    ]
    for path in MESH_ROOT.rglob("*"):
        if path.is_file() and should_scan_for_secrets(path):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in forbidden:
                if marker in text:
                    fail(f"possible secret marker {marker} in {path.relative_to(ROOT)}")


def main() -> None:
    validate_required_files()
    validate_optional_groups_root()
    validate_safety_needles()
    validate_default_root_has_no_workspace_provider()
    validate_no_obvious_secrets()
    print("PASS: Google Workspace Operations Terraform mesh scaffold is valid")
    print(f"validated_root={MESH_ROOT.relative_to(ROOT)}")
    print(f"required_files={len(REQUIRED_FILES)}")
    print(f"optional_workspace_group_files={len(OPTIONAL_GROUPS_REQUIRED_FILES)}")


if __name__ == "__main__":
    main()
