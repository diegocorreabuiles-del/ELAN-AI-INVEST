import pandas as pd


def compare_against_benchmark(
    strategy: pd.Series,
    benchmark: pd.Series,
):

    return {
        "strategy_return": strategy.iloc[-1],
        "benchmark_return": benchmark.iloc[-1],
        "alpha": strategy.iloc[-1] - benchmark.iloc[-1],
    }