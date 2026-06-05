SHELL := /bin/bash

# Prefer OpenTofu for new infrastructure work. Override with IAC=terraform if required.
IAC ?= tofu
WORKSPACE_MESH_DIR := infra/google-workspace-ops-mesh

.PHONY: help \
	doctor-workspace-ops \
	install-opentofu-macos \
	validate-workspace-prototype \
	validate-workspace-mesh \
	validate-workspace-all \
	terraform-workspace-mesh-init \
	terraform-workspace-mesh-fmt \
	terraform-workspace-mesh-validate \
	terraform-workspace-mesh-plan \
	tofu-workspace-mesh-init \
	tofu-workspace-mesh-fmt \
	tofu-workspace-mesh-validate \
	tofu-workspace-mesh-plan

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
	@echo ""
	@echo "Infrastructure mesh, defaults to IAC=tofu:"
	@echo "  make terraform-workspace-mesh-init"
	@echo "  make terraform-workspace-mesh-fmt"
	@echo "  make terraform-workspace-mesh-validate"
	@echo "  make terraform-workspace-mesh-plan"
	@echo ""
	@echo "OpenTofu aliases:"
	@echo "  make tofu-workspace-mesh-init"
	@echo "  make tofu-workspace-mesh-fmt"
	@echo "  make tofu-workspace-mesh-validate"
	@echo "  make tofu-workspace-mesh-plan"
	@echo ""
	@echo "Override binary when needed: make IAC=terraform terraform-workspace-mesh-plan"

doctor-workspace-ops:
	python3 scripts/check_workspace_ops.py

install-opentofu-macos:
	brew update
	brew install opentofu
	tofu -version

validate-workspace-prototype:
	python3 scripts/validate_google_workspace_ops_prototype.py

validate-workspace-mesh:
	python3 scripts/validate_google_workspace_ops_mesh.py

validate-workspace-all: validate-workspace-prototype validate-workspace-mesh

terraform-workspace-mesh-init:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) init

terraform-workspace-mesh-fmt:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) fmt -check

terraform-workspace-mesh-validate:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) validate

terraform-workspace-mesh-plan:
	cd $(WORKSPACE_MESH_DIR) && $(IAC) plan

# OpenTofu-named aliases retain the same implementation while making intent explicit.
tofu-workspace-mesh-init: terraform-workspace-mesh-init

tofu-workspace-mesh-fmt: terraform-workspace-mesh-fmt

tofu-workspace-mesh-validate: terraform-workspace-mesh-validate

tofu-workspace-mesh-plan: terraform-workspace-mesh-plan
