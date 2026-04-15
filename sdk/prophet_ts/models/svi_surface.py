from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd


@dataclass
class SVISurfaceModel:
    # Placeholder: store parameters of an SVI-like surface.
    # Real implementation would fit per timestamp (or use dynamic models) with no-arb constraints.
    params: Dict[str, Any] = None  # type: ignore

    def fit(self, df_surface: pd.DataFrame, **kwargs: Any) -> None:
        # df_surface columns might include: ts, maturity, strike, iv
        self.params = {}

    def predict(self, df_query: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        # df_query contains points (maturity, strike) at a given time
        return pd.DataFrame({"iv": []})
