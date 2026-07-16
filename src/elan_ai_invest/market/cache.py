from pathlib import Path

import pandas as pd


class MarketCache:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, symbol: str, data: pd.DataFrame) -> None:
        data.to_pickle(self.cache_dir / f"{symbol}.pkl")

    def load(self, symbol: str):
        path = self.cache_dir / f"{symbol}.pkl"
        return pd.read_pickle(path) if path.exists() else None
