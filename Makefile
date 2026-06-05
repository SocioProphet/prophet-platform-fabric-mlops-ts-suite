SHELL := /bin/bash

# Prefer OpenTofu for new infrastructure work. Override with IAC=terraform if required.
IAC ?= tofu
WORKSPACE_MESH_DIR := infra/google-workspace-ops-mesh
WORKSPACE_MESH_PLAN := $(WORKSPACE_MESH_DIR)/generated/google-workspace-ops-mesh/default.tfplan
WORKSPACE_MESH_PLAN_JSON := $(WORKSPACE_MESH_DIR)/generated/google-workspace-ops-mesh/default-plan.json

.PHONY: help \
	doctor-workspace-ops \
	install-opentofu-macos \
	validate-workspace-prototype \
	validate-workspace-mesh \
	validate-workspace-all \
	validate-workspace-mesh-plan-json \
	terraform-workspace-mesh-init \
	terraform-workspace-mesh-fmt \
	terraform-workspace-mesh-validate \
	terraform-workspace-mesh-plan \
	terraform-workspace-mesh-plan-out \
	terraform-workspace-mesh-plan-json \
	terraform-workspace-mesh-plan-safe \
	tofu-workspace-mesh-init \
	tofu-workspace-mesh-fmt \
	tofu-workspace-mesh-validate \
	tofu-workspace-mesh-plan \
	tofu-workspace-mesh-plan-safe

help:
	@echo "SocioProphet workspace operations targets"
	@echo ""
	@echo "Local readiness:"
	@echo "  make doctor-workspace-ops"
	@echo "  make install-opentofu-macos"
	@echo ""
	@echo "Validation:"
	@echo "  make validate-workspace-prototype"
	@echo "  make validate-workspace-mesh"
	@echo "  make validate-workspace-all"
	@echo "  make validate-workspace-mesh-plan-json"
	@echo ""
	@echo "Infrastructure mesh, defaults to IAC=tofu:"
	@echo "  make terraform-workspace-mesh-init"
	@echo "  make terraform-workspace-mesh-fmt"
	@echo "  make terraform-workspace-mesh-validate"
	@echo "  make terraform-workspace-mesh-plan"
	@echo "  make terraform-workspace-mesh-plan-safe"
	@echo ""
	@echo "OpenTofu aliases:"
	@echo "  make tofu-workspace-mesh-init"
	@echo "  make tofu-workspace-mesh-fmt"
	@echo "  make tofu-workspace-mesh-validate"
	@echo "  make tofu-workspace-mesh-plan"
	@echo "  make tofu-workspace-mesh-plan-safe"
	@echo ""
	@echo "Override binary when needed: make IAC=terraform terraform-workspace-mesh-plan"

doctor-workspace-ops:
	python3 scripts/check_workspace_ops.py

install-opentofu-macos:
	brew update
	HOMEBREW_NO_INSTALL_CLEANUP=1 brew install opentofu
	tofu -version

validate-workspace-prototype:
	python3 scripts/validate_google_workspace_ops_prototype.py

validate-workspace-mesh:
	python3 scripts/validate_google_workspace_ops_mesh.py

validate-workspace-all: validate-workspace-prototype validate-workspace-mesh

validate-workspace-mesh-plan-json:
	python3 scripts/validate_workspace_mesh_plan_json.py $(WORKSPACE_MESH_PLAN_JSON)

terraform-workspace-mesh-init:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) init

terraform-workspace-mesh-fmt:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) fmt -check

terraform-workspace-mesh-validate:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) validate

terraform-workspace-mesh-plan:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) plan

terraform-workspace-mesh-plan-out:
	mkdir -p $(dir $(WORKSPACE_MESH_PLAN))
	cd $(WORKSPACE_MESH_DIR) && $(IAC) plan -out=$(abspath $(WORKSPACE_MESH_PLAN))

terraform-workspace-mesh-plan-json: terraform-workspace-mesh-plan-out
	cd $(WORKSPACE_MESH_DIR) && $(IAC) show -json $(abspath $(WORKSPACE_MESH_PLAN)) > $(abspath $(WORKSPACE_MESH_PLAN_JSON))

terraform-workspace-mesh-plan-safe: terraform-workspace-mesh-plan-json validate-workspace-mesh-plan-json

# OpenTofu-named aliases retain the same implementation while making intent explicit.
tofu-workspace-mesh-init: terraform-workspace-mesh-init

tofu-workspace-mesh-fmt: terraform-workspace-mesh-fmt

tofu-workspace-mesh-validate: terraform-workspace-mesh-validate

tofu-workspace-mesh-plan: terraform-workspace-mesh-plan

tofu-workspace-mesh-plan-safe: terraform-workspace-mesh-plan-safe
