"""Prophet Time Series SDK (reference).

This is a reference SDK for:
- reading ProphetModelSpec YAML
- training/evaluating common time-series model families
- exporting artifacts in a consistent format for Prophet serving engines

This is intentionally lightweight and meant to be embedded into training images.
"""

from .spec import ProphetModelSpec, load_model_spec

from .io import load_dataset_from_uri
from .gating import apply_gates
