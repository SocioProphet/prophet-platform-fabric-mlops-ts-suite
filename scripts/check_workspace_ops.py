#!/usr/bin/env python3
"""Check local readiness for Workspace Ops prototype work.

This script is intentionally non-mutating. It does not install tools, change files,
or contact external services.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def status(label: str, value: str) -> None:
    print(f"{label}: {value}")


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def run_validator(path: str) -> None:
    subprocess.run([sys.executable, path], cwd=ROOT, check=True)


def main() -> None:
    print("Workspace Ops Local Check")
    print("=========================")
    status("repo_root", str(ROOT))

    makefile = ROOT / "Makefile"
    if not makefile.exists():
        fail("Makefile missing. Pull the latest repository changes.")

    makefile_text = makefile.read_text(encoding="utf-8")
    if "validate-workspace-all" not in makefile_text:
        fail("Makefile exists but lacks workspace targets. Pull the latest repository changes.")
    status("makefile", "workspace targets present")

    python_path = shutil.which("python3") or shutil.which("python")
    if not python_path:
        fail("Python not found")
    status("python", python_path)

    tofu_path = shutil.which("tofu")
    terraform_path = shutil.which("terraform")
    if tofu_path:
        status("iac_binary", f"tofu at {tofu_path}")
    elif terraform_path:
        status("iac_binary", f"terraform at {terraform_path}; OpenTofu remains preferred")
    else:
        status("iac_binary", "missing; install OpenTofu before mesh init/plan")

    print("\nRunning scaffold validators...")
    run_validator("scripts/validate_google_workspace_ops_prototype.py")
    run_validator("scripts/validate_google_workspace_ops_mesh.py")
    print("\nPASS: local repository scaffold is ready")


if __name__ == "__main__":
    main()
