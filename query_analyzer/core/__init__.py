"""Core module - Query Analysis Engine (v2.0.0).

v2.0.0 Highlights:
- AIAnalyzer: Generic LLM-based analysis (OpenAI-compatible)
- AIAnalysisResult: Structured AI recommendations
- Removed: AntiPatternDetector (moved to legacy/)

Legacy v1 components are available at query_analyzer.core.legacy.anti_pattern_detector
"""

from query_analyzer.core.ai_analyzer import AIAnalysisResult, AIAnalyzer

__all__ = [
    "AIAnalyzer",
    "AIAnalysisResult",
]
