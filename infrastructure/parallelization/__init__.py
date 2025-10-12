"""
並列化ユーティリティモジュール

このモジュールは、カスタムFCO分析の各レベルでの並列化を提供します：
- 銘柄レベル並列化（symbol_parallel_analyzer.py）
- 窓レベル並列化（custom_fco_engine.pyで実装済み）
"""

from .symbol_parallel_analyzer import analyze_symbols_parallel

__all__ = [
    'analyze_symbols_parallel',
]
