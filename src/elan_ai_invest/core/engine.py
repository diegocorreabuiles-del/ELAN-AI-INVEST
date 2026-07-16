from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from elan_ai_invest.core.config import Settings
from elan_ai_invest.core.models import AnalysisRequest, AnalysisResult
from elan_ai_invest.providers.base import MarketDataProvider
from elan_ai_invest.scoring import score_assets
from elan_ai_invest.storage import save_snapshot


class CoreEngine:
    """Coordinates data, scoring, market regime and persistence."""

    def __init__(
        self,
        settings: Settings,
        provider: MarketDataProvider,
        root: Path,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.root = root
        self.logger = logger

    def run_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        symbols = list(
            dict.fromkeys(symbol.strip().upper() for symbol in request.symbols if symbol.strip())
        )
        if not symbols:
            raise ValueError("Debes indicar al menos un activo")

        self.logger.info(
            "Inicio de análisis | activos=%s | periodo=%s", len(symbols), request.period
        )
        downloaded = self.provider.download_prices(symbols=symbols, period=request.period)
        if downloaded.prices.empty:
            self.logger.error("El proveedor no devolvió datos válidos")
            raise RuntimeError("No se pudieron descargar datos válidos")

        ranking = score_assets(
            downloaded.prices,
            self.settings.scoring,
            benchmark=self.settings.market.benchmark,
        )
        breadth = float(ranking["above_ma200"].mean() * 100) if not ranking.empty else 0.0
        avg_score = float(ranking["score"].mean()) if not ranking.empty else 0.0
        regime = self._detect_regime(ranking, breadth, avg_score)

        result = AnalysisResult(
            prices=downloaded.prices,
            ranking=ranking,
            errors=downloaded.errors,
            market_regime=regime,
            breadth_pct=breadth,
            average_score=avg_score,
        )

        if request.save_snapshot and not ranking.empty:
            db_path = self.root / self.settings.storage.database_path
            rows = save_snapshot(db_path, ranking, result.captured_at.isoformat(timespec="seconds"))
            self.logger.info("Fotografía guardada | filas=%s", rows)

        self.logger.info(
            "Fin de análisis | correctos=%s | errores=%s | régimen=%s | score_medio=%.1f",
            result.successful_symbols,
            len(result.errors),
            result.market_regime,
            result.average_score,
        )
        return result

    @staticmethod
    def _detect_regime(ranking: pd.DataFrame, breadth: float, avg_score: float) -> str:
        if ranking.empty:
            return "Sin datos"
        if breadth >= 65 and avg_score >= 60:
            return "Alcista"
        if breadth <= 35 or avg_score < 45:
            return "Defensivo"
        return "Mixto"
