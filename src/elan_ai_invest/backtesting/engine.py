from .metrics import calculate_metrics
from .report import build_report
from .strategy import run_strategy


class BacktestEngine:
    def run(self, prices, signals):
        equity = run_strategy(prices, signals)
        return build_report(equity, calculate_metrics(equity))
