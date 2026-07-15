from .allocator import allocate
from .constraints import apply_constraints
from .filters import filter_assets
from .weights import calculate_weights


class DecisionEngine:

    def build_portfolio(self, ranking):

        ranking = filter_assets(ranking)

        ranking = calculate_weights(ranking)

        ranking = apply_constraints(ranking)

        return allocate(ranking)