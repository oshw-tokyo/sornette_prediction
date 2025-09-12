"""
FCOエンジンのテストコード
Boulder lppls統合と論文再現の両立を確認
"""

import numpy as np
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.fitting.fco_engine import FCOEngine, FCOAnalysisResult


def generate_bubble_data(n_points: int = 1000, bubble_type: str = 'positive') -> np.ndarray:
    """
    テスト用のバブルデータを生成
    
    Args:
        n_points: データ点数
        bubble_type: 'positive' or 'negative'
    
    Returns:
        価格データ
    """
    t = np.linspace(0, 1, n_points)
    tc = 1.2  # 臨界時間
    m = 0.35  # べき乗指数
    omega = 7.0  # 角周波数
    
    # LPPLS式でデータ生成
    dt = tc - t
    dt[dt <= 0] = 1e-8  # 負の値を回避
    
    base = 100  # 基準価格
    trend = 50 * np.power(dt, m)
    oscillation = 10 * np.power(dt, m) * np.cos(omega * np.log(dt))
    
    if bubble_type == 'positive':
        prices = base + trend + oscillation
    else:
        prices = base - trend - oscillation
    
    # ノイズを追加
    noise = np.random.normal(0, 0.5, n_points)
    prices = prices + noise
    
    return prices


def test_fco_engine_basic():
    """FCOエンジンの基本動作テスト"""
    print("\n" + "="*60)
    print("FCOエンジン基本動作テスト")
    print("="*60)
    
    # エンジン初期化
    engine = FCOEngine(use_parallel=False, max_workers=1)
    print("✓ FCOエンジン初期化成功")
    
    # テストデータ生成
    prices = generate_bubble_data(n_points=800, bubble_type='positive')
    print(f"✓ テストデータ生成: {len(prices)}点")
    
    # DS-LPPLS Confidence計算
    print("\n多重時間窓分析を実行中...")
    result = engine.compute_ds_lppls_confidence(prices)
    
    # 結果確認
    print("\n--- 分析結果 ---")
    print(f"DS-LPPLS Confidence (正): {result.ds_lppls_confidence:.2%}")
    print(f"DS-LPPLS Confidence (負): {result.ds_lppls_confidence_neg:.2%}")
    print(f"バブルタイプ: {result.bubble_type}")
    
    if result.predicted_tc:
        print(f"予測臨界時間: {result.predicted_tc:.3f}")
        print(f"標準偏差: {result.tc_std:.3f}")
        print(f"シナリオ確率: {result.scenario_probability:.2%}")
    
    print(f"分析窓数: {result.metadata.get('num_windows', 0)}")
    
    # アサーション
    assert isinstance(result, FCOAnalysisResult), "結果の型が不正"
    assert 0 <= result.ds_lppls_confidence <= 1, "Confidence値が範囲外"
    assert result.bubble_type in ['positive', 'negative', 'none'], "バブルタイプが不正"
    
    print("\n✅ 基本動作テスト成功")
    return True


def test_paper_reproduction():
    """論文再現テスト機能の確認"""
    print("\n" + "="*60)
    print("論文再現テスト機能確認")
    print("="*60)
    
    engine = FCOEngine(use_parallel=False)
    
    # 1987年風のデータを生成（706点）
    prices = generate_bubble_data(n_points=706, bubble_type='positive')
    print(f"✓ 1987年風データ生成: {len(prices)}点")
    
    # 論文再現テスト実行
    print("\n論文再現テストを実行中...")
    result = engine.validate_paper_reproduction(prices, test_case='1987')
    
    print("\n--- 検証結果 ---")
    print(f"スコア: {result['score']}/100")
    print(f"ステータス: {result['status']}")
    
    if 'parameters' in result:
        params = result['parameters']
        print(f"パラメータ m: {params.get('m', 'N/A')}")
        print(f"パラメータ ω: {params.get('w', 'N/A')}")
    
    print("\n✅ 論文再現テスト機能確認完了")
    return True


def test_single_window_compatibility():
    """単一窓フィッティングの互換性テスト"""
    print("\n" + "="*60)
    print("単一窓フィッティング互換性テスト")
    print("="*60)
    
    engine = FCOEngine()
    prices = generate_bubble_data(n_points=500)
    
    # 単一窓フィッティング
    print("\n単一窓フィッティングを実行中...")
    result = engine.fit_single_window(prices, window_size=365)
    
    print("\n--- フィッティング結果 ---")
    for key, value in result.items():
        if isinstance(value, (int, float)):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")
    
    # 基本的なパラメータが存在することを確認
    assert 'm' in result or 'beta' in result, "べき乗指数が見つからない"
    assert 'w' in result or 'omega' in result, "角周波数が見つからない"
    
    print("\n✅ 互換性テスト成功")
    return True


def test_insufficient_data_handling():
    """データ不足時の処理テスト"""
    print("\n" + "="*60)
    print("データ不足時の処理テスト")
    print("="*60)
    
    engine = FCOEngine()
    
    # 少ないデータ（200点）
    prices = generate_bubble_data(n_points=200)
    print(f"✓ 少量データ生成: {len(prices)}点")
    
    # 分析実行（エラーにならないことを確認）
    print("\n少量データで分析を実行中...")
    result = engine.compute_ds_lppls_confidence(prices)
    
    print(f"✓ 分析完了: Confidence={result.ds_lppls_confidence:.2%}")
    print(f"  窓数調整: {result.metadata.get('num_windows', 0)}窓で分析")
    
    assert result is not None, "結果がNone"
    print("\n✅ データ不足処理テスト成功")
    return True


def main():
    """全テストを実行"""
    print("\n" + "="*70)
    print(" FCOエンジン統合テスト ")
    print("="*70)
    
    tests = [
        ("基本動作", test_fco_engine_basic),
        ("論文再現", test_paper_reproduction),
        ("単一窓互換性", test_single_window_compatibility),
        ("データ不足処理", test_insufficient_data_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ PASSED"))
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            results.append((name, f"❌ FAILED: {str(e)[:50]}"))
    
    # 結果サマリー
    print("\n" + "="*70)
    print(" テスト結果サマリー ")
    print("="*70)
    for name, status in results:
        print(f"{name:20} {status}")
    
    # 全体の成功判定
    all_passed = all("PASSED" in status for _, status in results)
    if all_passed:
        print("\n🎉 全テスト成功！FCOエンジン統合準備完了")
    else:
        print("\n⚠️  一部テスト失敗。修正が必要です。")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)