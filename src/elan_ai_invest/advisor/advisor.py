from __future__ import annotations

import pandas as pd

from .explanations import explain
from .ranking import rank_assets
from .recommendations import build_recommendation


class AIAdvisor:

    def analyze(self, ranking: pd.DataFrame, portfolio: object) -> dict[str, object]:

        ranked = rank_assets(ranking)

        recommendation = build_recommendation(
            ranked,
            portfolio,
        )

        recommendation["explanation"] = explain(recommendation)

        return recommendation
