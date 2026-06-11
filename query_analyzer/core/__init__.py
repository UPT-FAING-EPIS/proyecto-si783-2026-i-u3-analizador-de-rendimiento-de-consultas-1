"""Core module - Query Analysis Engine (v2.0.0).

The core exposes optional AI interpretation. Engine observations are produced
by adapters and kept separate from generated language.
"""

from query_analyzer.core.ai_analyzer import AIAnalysisResult, AIAnalyzer
from query_analyzer.core.connection_diagnostics import (
    ConnectionDiagnostic,
    ConnectionDiagnosticsService,
    DiagnosticCheck,
)

__all__ = [
    "AIAnalyzer",
    "AIAnalysisResult",
    "ConnectionDiagnostic",
    "ConnectionDiagnosticsService",
    "DiagnosticCheck",
]
