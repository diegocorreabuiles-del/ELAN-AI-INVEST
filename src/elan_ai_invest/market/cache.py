from pathlib import Path
import pandas as pd


class MarketCache:

    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, symbol: str, data: pd.DataFrame):
        data.to_parquet(self.cache_dir / f"{symbol}.parquet")

    def load(self, symbol: str):

        file = self.cache_dir / f"{symbol}.parquet"

        if not file.exists():
            return None

        return pd.read_parquet(file)