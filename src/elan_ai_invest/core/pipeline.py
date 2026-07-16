"""Compatibility adapter for the legacy pre-CoreEngine pipeline.

``CoreEngine`` is the canonical production pipeline. ``InvestmentPipeline``
is preserved at its historical import path for one compatibility cycle.
"""

from elan_ai_invest.legacy.pipeline_v1 import InvestmentPipeline

__all__ = ["InvestmentPipeline"]
