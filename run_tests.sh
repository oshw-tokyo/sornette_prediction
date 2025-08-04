#!/bin/bash
# Sornette Prediction System - Unified Test Runner
# プロジェクト方針に従い、entry_points/main.pyを経由してテストを実行

echo "🧪 Sornette Prediction System - Test Suite"
echo "=========================================="
echo "🚀 統一エントリーポイント経由でテスト実行中..."
echo ""

# 必要なディレクトリの確認・作成
echo "📁 必要なディレクトリの確認..."
mkdir -p results/test_results
mkdir -p analysis_results/{plots,summaries,metrics,raw_data,logs}

# 環境確認
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Please activate one if needed."
fi

echo ""
echo "🎯 論文再現テスト（最重要）"
echo "--------------------------------"

# 1987年ブラックマンデー検証（100/100スコア保護対象）
echo "🔍 1987 Black Monday validation (100/100 score required)..."
python entry_points/main.py validate --crash 1987

# 結果確認
if [ $? -eq 0 ]; then
    echo "✅ 1987 validation: PASSED"
else
    echo "❌ 1987 validation: FAILED - CRITICAL ISSUE!"
    echo "🚨 論文再現機能が破損しています。即座に修正が必要です。"
    exit 1
fi

echo ""
echo "🔬 追加検証テスト"
echo "--------------------------------"

# 2000年ドットコムバブル検証
echo "🔍 2000 Dotcom Bubble validation..."
python entry_points/main.py validate --crash 2000

# 全体検証
echo ""
echo "🌍 全体検証テスト..."
python entry_points/main.py validate --crash all

# 全体の結果確認
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 All validation tests completed!"
    echo "✅ 論文再現機能: 正常動作確認"
    echo "✅ システム整合性: 検証済み"
    echo ""
    echo "📊 テスト結果はresults/test_results/に保存されました"
    exit 0
else
    echo ""
    echo "❌ Some validation tests failed."
    echo "🔧 詳細は上記のログを確認してください。"
    exit 1
fi