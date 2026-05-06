.PHONY: validate validate-world-signal-mlops-packs

validate: validate-world-signal-mlops-packs

validate-world-signal-mlops-packs:
	python3 tools/validate_world_signal_mlops_packs.py
