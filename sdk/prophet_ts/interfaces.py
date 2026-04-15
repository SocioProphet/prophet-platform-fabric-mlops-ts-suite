from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class ForecastResult:
    # Minimal standard output. Extend as needed.
    mean: pd.DataFrame  # columns: [ts, sym, yhat]
    quantiles: Optional[pd.DataFrame] = None  # columns include q0.1, q0.5, q0.9 etc.
    params: Optional[Dict[str, Any]] = None  # distribution params, metadata


class ForecastModel(ABC):
    @abstractmethod
    def fit(self, df: pd.DataFrame, *, timestamp: str, target: str, group: str, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> ForecastResult:
        raise NotImplementedError

    def explain(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}

    def diagnostics(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}


class RiskModel(ABC):
    @abstractmethod
    def fit(self, df: pd.DataFrame, *, timestamp: str, target: str, group: str, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict_vol(self, df_context: pd.DataFrame, *, horizon: int, **kwargs: Any) -> pd.DataFrame:
        raise NotImplementedError


class Simulator(ABC):
    @abstractmethod
    def sample_paths(self, df_context: pd.DataFrame, *, horizon: int, n: int, **kwargs: Any) -> Any:
        raise NotImplementedError
