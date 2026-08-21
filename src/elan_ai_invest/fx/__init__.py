"""Foreign-exchange registry, routing, history and analytics."""

from .analytics import (
    CORRELATION_PERIODS,
    ROLLING_WINDOWS,
    CorrelationMatrixResult,
    CorrelationStatistics,
    FxKpis,
    compute_fx_kpis,
    correlation_matrix,
    correlation_statistics,
    log_returns,
    rolling_correlation,
)
from .catalog import build_virtual_fx_catalog, search_fx_pairs
from .history import (
    HistoricalFxService,
    ProviderHistory,
    invert_fx_history,
    multiply_fx_histories,
    provider_history,
    sanitize_fx_history,
)
from .models import (
    Currency,
    FxHistory,
    FxPair,
    FxRoute,
    FxRouteLeg,
    FxSourceType,
    ProviderPair,
    is_fx_asset_id,
    normalize_currency_code,
    normalize_fx_pair,
)
from .providers import YahooFxHistoryProvider
from .quality import (
    FxQualityIncident,
    FxQualityReport,
    assess_fx_quality,
    validate_inverse_consistency,
    validate_triangular_consistency,
)
from .registry import CurrencyRegistry, load_currency_registry
from .routing import FxRoutingEngine, calculate_cross_rate, invert_fx_rate

__all__ = [
    "CORRELATION_PERIODS",
    "ROLLING_WINDOWS",
    "CorrelationMatrixResult",
    "CorrelationStatistics",
    "Currency",
    "CurrencyRegistry",
    "FxHistory",
    "FxKpis",
    "FxPair",
    "FxQualityIncident",
    "FxQualityReport",
    "FxRoute",
    "FxRouteLeg",
    "FxRoutingEngine",
    "FxSourceType",
    "HistoricalFxService",
    "ProviderHistory",
    "ProviderPair",
    "YahooFxHistoryProvider",
    "assess_fx_quality",
    "build_virtual_fx_catalog",
    "calculate_cross_rate",
    "compute_fx_kpis",
    "correlation_matrix",
    "correlation_statistics",
    "invert_fx_history",
    "invert_fx_rate",
    "is_fx_asset_id",
    "load_currency_registry",
    "log_returns",
    "multiply_fx_histories",
    "normalize_currency_code",
    "normalize_fx_pair",
    "provider_history",
    "rolling_correlation",
    "sanitize_fx_history",
    "search_fx_pairs",
    "validate_inverse_consistency",
    "validate_triangular_consistency",
]
