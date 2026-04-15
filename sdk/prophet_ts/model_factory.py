from __future__ import annotations

import dataclasses
from typing import Any, Dict, Type

from .models.arima import ARIMAForecaster
from .models.garch import GARCHVolatilityModel
from .models.gbm import GBMForecaster
from .models.seq2seq import Seq2SeqForecaster
from .models.transformer import TransformerForecaster
from .models.svi_surface import SVISurfaceModel


_FAMILY_MAP: Dict[str, Type[Any]] = {
    # classical
    "arima": ARIMAForecaster,
    "sarima": ARIMAForecaster,
    "arma": ARIMAForecaster,
    "gbm": GBMForecaster,
    "xgboost": GBMForecaster,
    "lightgbm": GBMForecaster,
    "catboost": GBMForecaster,
    # deep
    "deep.seq2seq": Seq2SeqForecaster,
    "seq2seq": Seq2SeqForecaster,
    "rnn": Seq2SeqForecaster,
    "lstm": Seq2SeqForecaster,
    "gru": Seq2SeqForecaster,
    "deep.transformer": TransformerForecaster,
    "transformer": TransformerForecaster,
    # risk
    "garch": GARCHVolatilityModel,
    "arch": GARCHVolatilityModel,
    # surfaces
    "svi": SVISurfaceModel,
    "iv_surface": SVISurfaceModel,
    "surface.svi": SVISurfaceModel,
}


def _filter_kwargs(cls: Type[Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Only pass kwargs that the dataclass (or class) actually accepts."""
    if dataclasses.is_dataclass(cls):
        allowed = {f.name for f in dataclasses.fields(cls) if f.init}
        return {k: v for k, v in kwargs.items() if k in allowed}
    return kwargs


def build_model(family: str, **kwargs: Any) -> Any:
    fam = (family or "").lower()
    cls = _FAMILY_MAP.get(fam)
    if cls is None:
        raise ValueError(f"Unknown model family: {family}")

    # Coerce common shapes
    if "order" in kwargs and isinstance(kwargs["order"], list):
        kwargs["order"] = tuple(kwargs["order"])

    filtered = _filter_kwargs(cls, dict(kwargs))
    return cls(**filtered)
