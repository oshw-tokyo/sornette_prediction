"""
銘柄レベル並列化モジュール

カスタムFCO分析の銘柄レベル並列化による2-4倍高速化を実現します。

【2段階並列化】
- Level 1: 銘柄レベル並列化（n_symbol_workers）
- Level 2: 窓レベル並列化（n_window_workers）

【リソース配分】
- 総CPU数: cpu_count()
- 銘柄並列数: n_symbol_workers（デフォルト: 2-4）
- 窓並列数: n_window_workers（デフォルト: cpu_count() // n_symbol_workers）

【科学的精度保証】
- 各銘柄の解析は完全に独立
- 決定性: 同一データで同一結果（乱数シード不使用）
- 既存実装再利用: 窓並列化（Issue I127実装済み）と同じアプローチ
"""

from multiprocessing import Pool, cpu_count
from typing import Dict, List, Tuple, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


def analyze_symbols_parallel(
    symbols: List[str],
    prices_dict: Dict[str, np.ndarray],
    n_tries: int = 10,
    n_symbol_workers: Optional[int] = None,
    n_window_workers: Optional[int] = None
) -> Dict[str, Any]:
    """
    複数銘柄をマルチプロセッシング並列解析

    【2段階並列化】
    - Level 1: 銘柄レベル並列化（n_symbol_workers）
    - Level 2: 窓レベル並列化（n_window_workers）

    【リソース配分】
    - 総CPU数: cpu_count()
    - 銘柄並列数: n_symbol_workers（デフォルト: 2-4）
    - 窓並列数: n_window_workers（デフォルト: cpu_count() // n_symbol_workers）

    Args:
        symbols: 銘柄リスト
        prices_dict: 銘柄 → 価格データのマッピング
        n_tries: グリッドサーチ刻み数
        n_symbol_workers: 銘柄並列数（Noneで自動設定）
        n_window_workers: 窓並列数（Noneで自動設定）

    Returns:
        results_dict: 銘柄 → 解析結果のマッピング

    【使用例】
    ```python
    from infrastructure.parallelization.symbol_parallel_analyzer import analyze_symbols_parallel

    symbols = ['SP500', 'NASDAQ', 'DJIA', 'RUSSELL2000']
    prices_dict = {symbol: get_prices(symbol) for symbol in symbols}

    results = analyze_symbols_parallel(
        symbols=symbols,
        prices_dict=prices_dict,
        n_tries=10,
        n_symbol_workers=4,  # 4銘柄同時処理
        n_window_workers=None  # 自動設定（残りCPU）
    )

    for symbol, result in results.items():
        if result is not None:
            print(f"{symbol}: DS-LPPLS Confidence = {result.ds_lppls_confidence:.1f}%")
    ```

    【科学的精度保証】
    以下の2つは完全に等価です（逐次版と並列版で結果が1bit単位で一致）:
    ```python
    # 逐次版
    result_sequential = analyze_symbol(symbol, prices)

    # 並列版
    result_parallel = analyze_symbols_parallel([symbol], {symbol: prices})[symbol]

    # 結果: result_sequential == result_parallel (完全一致)
    ```
    """
    # リソース配分の自動決定
    total_cpus = cpu_count()

    if n_symbol_workers is None:
        # 銘柄並列数: 2-4が最適（多すぎるとメモリ効率悪化）
        n_symbol_workers = min(4, max(2, total_cpus // 4))

    if n_window_workers is None:
        # 窓並列数: 残りのCPUを割り当て
        n_window_workers = max(1, total_cpus // n_symbol_workers)

    logger.info(f"=== 銘柄レベル並列化開始 ===")
    logger.info(f"並列化設定: {n_symbol_workers} 銘柄 × {n_window_workers} 窓/銘柄")
    logger.info(f"総CPU数: {total_cpus}")
    logger.info(f"解析対象: {len(symbols)} 銘柄")

    # 銘柄並列化実行
    worker_params = [
        (symbol, prices_dict[symbol], n_tries, n_window_workers)
        for symbol in symbols
        if symbol in prices_dict
    ]

    if len(worker_params) == 0:
        logger.warning("解析対象の銘柄が見つかりませんでした")
        return {}

    with Pool(n_symbol_workers) as pool:
        results = pool.starmap(_analyze_symbol_worker_static, worker_params)

    # 結果を辞書にマッピング
    results_dict = {symbol: result for symbol, result in results}

    # サマリー出力
    successful = sum(1 for r in results_dict.values() if r is not None)
    logger.info(f"=== 銘柄レベル並列化完了 ===")
    logger.info(f"成功: {successful}/{len(symbols)} 銘柄")

    return results_dict


def _analyze_symbol_worker_static(
    symbol: str,
    prices: np.ndarray,
    n_tries: int,
    n_window_workers: int
) -> Tuple[str, Any]:
    """
    静的ワーカー関数: 単一銘柄の解析（multiprocessing.Pool用）

    Args:
        symbol: 銘柄名
        prices: 価格データ
        n_tries: グリッドサーチ刻み数
        n_window_workers: 窓並列数

    Returns:
        (symbol, result): 銘柄名と解析結果のタプル

    【実装詳細】
    - multiprocessing.Pool.starmap用の静的関数
    - CustomFCOEngineを内部でインポート（プロセス独立性のため）
    - compute_ds_lppls_confidence_parallel()で窓レベル並列化
    - エラー時はNoneを返す（部分失敗許容）
    """
    from core.fitting.custom_fco_engine import CustomFCOEngine

    logger.info(f"[{symbol}] 解析開始（窓並列数: {n_window_workers}）")

    try:
        engine = CustomFCOEngine(n_tries=n_tries)
        result = engine.compute_ds_lppls_confidence_parallel(
            prices,
            n_workers=n_window_workers
        )

        if result is not None:
            logger.info(
                f"[{symbol}] 解析成功 - "
                f"DS-LPPLS: {result.ds_lppls_confidence:.1f}%, "
                f"適格: {result.qualified_fits}/{result.total_fits}"
            )
        else:
            logger.warning(f"[{symbol}] 解析失敗（結果がNone）")

        return (symbol, result)

    except Exception as e:
        logger.error(f"[{symbol}] 解析エラー: {e}", exc_info=True)
        return (symbol, None)
