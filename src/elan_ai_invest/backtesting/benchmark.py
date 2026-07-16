def compare_against_benchmark(strategy, benchmark):
    strategy_return = float(strategy.iloc[-1] / strategy.iloc[0] - 1)
    benchmark_return = float(benchmark.iloc[-1] / benchmark.iloc[0] - 1)
    return {"strategy_return": strategy_return, "benchmark_return": benchmark_return, "alpha": strategy_return - benchmark_return}
