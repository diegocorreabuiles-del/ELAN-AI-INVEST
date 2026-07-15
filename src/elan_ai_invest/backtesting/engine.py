from .strategy import run_strategy
from .metrics import calculate_metrics
from .report import build_report


class BacktestEngine:

    def run(self, prices, signals):

        equity = run_strategy(prices, signals)

        metrics = calculate_metrics(equity)

        return build_report(equity, metrics)