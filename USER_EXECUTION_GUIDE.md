# 🎯 LPPL市場クラッシュ予測システム - ユーザー実行ガイド

このガイドに従って、あなた自身でLPPL市場クラッシュ予測分析を実行できます。

## 📋 目次
1. [環境構築](#環境構築)
2. [基本的な市場分析](#基本的な市場分析)
3. [包括的市場分析](#包括的市場分析)
4. [品質評価付き分析](#品質評価付き分析)
5. [過去時点分析](#過去時点分析)
6. [UIダッシュボード](#uiダッシュボード)
7. [トラブルシューティング](#トラブルシューティング)

---

## 🔧 環境構築

### 1. 前提条件
- Python 3.8以上
- インターネット接続（データ取得のため）

### 2. 依存関係インストール
```bash
# プロジェクトディレクトリに移動
cd /path/to/sornette_prediction

# 仮想環境作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 依存関係インストール
pip install -r requirements.txt
```

### 3. 環境変数設定
```bash
# .envファイルを作成
cp .env.example .env

# FRED APIキーを設定（必要に応じて）
# .envファイル内のFRED_API_KEYを設定
```

---

## 📊 基本的な市場分析

### 1. 単一市場の簡易分析
```bash
# 統一エントリーポイントからの実行（推奨）
python entry_points/main.py analyze NASDAQCOM --period 1y

# カタログ全銘柄の包括解析
python entry_points/main.py analyze ALL

# 市場リスク分析
python entry_points/main.py analyze MARKET
```

**期待される出力**:
- LPPL パラメータ（tc, β, ω）
- 予測クラッシュ日
- R²値とRMSE
- 可視化グラフ

### 2. 現在のNASDAQ状況確認
```bash
# 統一エントリーポイント経由でNASDAQ分析
python entry_points/main.py analyze NASDAQCOM --period 1y
```

**確認ポイント**:
- 品質評価結果
- 境界張り付きの有無
- 使用可能候補数
- 信頼度スコア

---

## 🌍 包括的市場分析

### 1. 複数市場の同時分析
```bash
# マーケットデータカタログv2.0による包括分析
python entry_points/main.py analyze ALL

# 市場リスク分析（全市場の統合分析）
python entry_points/main.py analyze MARKET
```

**期待される結果**:
- **16銘柄・7カテゴリ**の包括分析（crypto, indices, sectors, REITs等）
- **4段階リスク評価**（CRITICAL/HIGH/MEDIUM/LOW）
- **投資判断支援**（ポジションサイズ推奨付き）
- **APIレート制限管理**（自動待機・進捗表示）
- 可視化レポート生成

---

## 🧪 システム検証・テスト

### 1. 論文再現テスト（最重要）
```bash
# 1987年ブラックマンデー検証（100/100スコア必須）
python entry_points/main.py validate --crash 1987

# 2000年ドットコムバブル検証
python entry_points/main.py validate --crash 2000

# 全検証テスト実行
python entry_points/main.py validate --crash all
```

**期待される結果**:
- **1987年検証**: 100/100スコア維持必須（科学的根幹保護）
- **2000年検証**: 定性的検証合格
- システム整合性確認

### 2. 統合テストスイート
```bash
# 統一テストランナー実行
./run_tests.sh
```

**実行内容**:
- 論文再現テスト（1987年ブラックマンデー）
- 追加検証テスト（2000年ドットコムバブル）
- システム全体整合性確認
- 環境・依存関係チェック

---

## 📊 分析結果の確認

### 2. 結果の確認
```bash
# 結果ディレクトリの確認
ls results/comprehensive_analysis/

# CSVファイルの内容表示
cat results/comprehensive_analysis/market_risk_report_*.csv
```

---

## 🔍 品質評価付き分析

### 1. 品質評価システムの基本テスト
```python
# Pythonインタラクティブモードで実行
python

>>> from core.fitting.fitting_quality_evaluator import FittingQualityEvaluator
>>> evaluator = FittingQualityEvaluator()

# 境界張り付きケースのテスト
>>> params = {'tc': 1.001, 'beta': 0.35, 'omega': 6.5}
>>> stats = {'r_squared': 0.95, 'rmse': 0.03}
>>> assessment = evaluator.evaluate_fitting(params, stats)
>>> print(f"品質: {assessment.quality.value}")
>>> print(f"使用可能: {assessment.is_usable}")
>>> print(f"問題: {assessment.issues}")
```

### 2. 多基準選択システムの実行
```python
>>> from core.fitting.multi_criteria_selection import MultiCriteriaSelector
>>> import pandas as pd
>>> import numpy as np

# サンプルデータ生成
>>> dates = pd.date_range('2020-01-01', periods=1000, freq='D')
>>> prices = np.exp(5 + 0.1 * np.random.randn(1000).cumsum())
>>> data = pd.DataFrame({'Close': prices}, index=dates)

# 多基準選択実行
>>> selector = MultiCriteriaSelector()
>>> result = selector.perform_comprehensive_fitting(data)

# 結果確認
>>> print(f"総候補数: {len(result.all_candidates)}")
>>> for criteria, candidate in result.selections.items():
...     if candidate:
...         print(f"{criteria.value}: tc={candidate.tc:.3f}")
```

---

## 📈 過去時点分析

### 1. NASDAQ過去時点分析の実行
```bash
# 過去6ヶ月間の系統的分析
python retrospective_nasdaq_analysis.py
```

**期待される結果**:
- 過去26週間のtc値推移
- 予測の安定性評価
- 境界張り付き問題の時系列確認
- 詳細可視化

### 2. 結果の解釈
```bash
# 分析結果の確認
ls results/retrospective_analysis/

# CSV データの確認
head -20 results/retrospective_analysis/nasdaq_retrospective_data_*.csv
```

**確認すべき指標**:
- tc値の時系列変化
- 予測日の変動
- R²値の安定性
- 品質評価の推移

---

## 📊 定期解析システム

### 1. スケジュール解析実行
```bash
# 通常の定期解析実行
python entry_points/main.py scheduled-analysis run

# バックフィル実行（従来版）
python entry_points/main.py scheduled-analysis backfill --start 2025-01-01 --end 2025-08-01

# 🆕 バックフィル実行（高効率版 v2）
python entry_points/main.py scheduled-analysis backfill-v2 --start 2025-01-01 --end 2025-08-01

# ドライラン（実行シミュレーション）
python entry_points/main.py scheduled-analysis backfill-v2 --start 2025-01-01 --end 2025-08-01 --dry-run
```

### 2. Backfill v2の特徴

**API効率化**:
- **従来版**: N期間 × M銘柄 = N×M回のAPIコール
- **v2版**: M銘柄 = M回のAPIコール（N倍効率化）
- **実測例**: 3期間×3銘柄で66.7%のAPI呼び出し削減

**対応データソース**:
- **FRED**: 制限なし、最大期間一括取得
- **Alpha Vantage**: 20年以上の履歴を一括取得
- **CoinGecko**: 365日制限を自動分割して取得・結合

**使用例**:
```bash
# 過去1年間の週次データを効率的にバックフィル
python entry_points/main.py scheduled-analysis backfill-v2 \
  --start 2024-08-01 --end 2025-08-01 \
  --schedule fred_weekly

# テスト実行（DB保存なし）
python entry_points/main.py scheduled-analysis backfill-v2 \
  --start 2025-07-01 --end 2025-08-01 \
  --dry-run
```

---

## 🎛️ UIダッシュボード

### 1. Streamlitダッシュボードの起動
```bash
# ダッシュボード起動（統一エントリーポイント）
python entry_points/main.py dashboard --type main

# 旧実装（シンボル別ダッシュボード）
python entry_points/main.py dashboard --type symbol
```

### 2. ダッシュボードの使用方法

**基本操作**:
1. ブラウザでlocalhost:8501にアクセス
2. サイドバーで市場・期間を選択
3. "分析実行"ボタンをクリック
4. 結果を各タブで確認

**タブの説明**:
- **最新結果比較**: 各選択基準での結果比較
- **時系列トレンド**: tc値の時間的変化
- **統計サマリー**: 各基準の統計情報
- **詳細分析**: 個別セッションの詳細

---

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. データ取得エラー
```
エラー: FRED API接続失敗
```
**解決策**:
- インターネット接続を確認
- FRED_API_KEYが正しく設定されているか確認
- APIの利用制限に引っかかっていないか確認

#### 2. 依存関係エラー
```
ModuleNotFoundError: No module named 'xxx'
```
**解決策**:
```bash
pip install -r requirements.txt
pip install --upgrade pip
```

#### 3. メモリ不足エラー
```
MemoryError during fitting
```
**解決策**:
- データ期間を短縮
- 初期値セット数を削減
- より高性能なマシンを使用

#### 4. 境界張り付き警告
```
品質: boundary_stuck
使用可能: False
```
**解釈**:
- これは正常な動作です
- 境界張り付きは品質評価により適切に検出されています
- 使用可能な他の候補を確認してください

#### 4.1. tc下限張り付き（CRITICAL_PROXIMITY）
```
品質: critical_proximity
使用可能: False
解釈: フィッティングエラー：tc下限境界張り付き
```
**解釈**:
- 主にフィッティングの数値的問題
- パラメータ最適化がtc下限に張り付いた状態
- 予測には使用不可（フィッティング失敗として扱う）
- 異なる初期値・期間・手法での再試行を推奨

#### 5. 全候補が使用不可
```
使用可能候補: 0
```
**対処法**:
1. データ期間を変更
2. 別の市場で分析
3. 境界条件を調整
4. より長期間のデータを使用

---

## 📊 実行例とサンプル出力

### 成功例
```
🎯 包括的市場クラッシュ予測分析
======================================================================

📊 分析サマリー:
   総分析市場数: 5
   高リスク市場: 2
   中リスク市場: 1
   監視推奨市場: 2

🚨 高リスク市場 (tc ≤ 1.3):
   NASDAQ (NASDAQCOM):
     - tc値: 1.124
     - 予測クラッシュ日: 2025-09-15
     - 信頼度: 85.3%
     - R²: 0.891

📊 詳細レポート保存: results/comprehensive_analysis/market_risk_report_20250802_183456.csv
📊 可視化保存: results/comprehensive_analysis/risk_visualization_20250802_183456.png
```

### 品質評価例
```
🔍 品質評価結果:
   品質: high_quality
   信頼度: 91.25%
   使用可能: True
   問題: []
   
   メタデータ:
   - overall_score: 0.913
   - parameter_stability: 0.856
   - theoretical_validity: 0.923
```

---

## 💡 高度な使用方法

### 1. カスタム分析パラメータ
```python
# カスタム期間での分析
from src.monitoring.multi_market_monitor import MultiMarketMonitor

monitor = MultiMarketMonitor()
custom_result = monitor.analyze_market_window(
    MarketIndex.NASDAQ, 
    TimeWindow.EXTENDED,  # 5年
    end_date=datetime(2024, 12, 31)
)
```

### 2. 独自データでの分析
```python
# 独自CSVデータの読み込み
import pandas as pd

custom_data = pd.read_csv('your_market_data.csv', 
                         index_col='Date', 
                         parse_dates=True)

# 必要なカラム: 'Close'
selector = MultiCriteriaSelector()
result = selector.perform_comprehensive_fitting(custom_data)
```

### 3. バッチ処理
```bash
# 複数市場の自動分析
for market in NASDAQ SP500 DJIA; do
    echo "分析中: $market"
    python single_market_analysis.py --market $market --period 730
done
```

---

## 📞 サポート

問題が発生した場合:
1. このガイドのトラブルシューティングを確認
2. ログファイルを確認（logs/ディレクトリ）
3. GitHubのIssuesページで報告
4. 実行環境の詳細を記録（OS、Pythonバージョン等）

**重要**: このシステムは研究・教育目的です。実際の投資判断には使用しないでください。

---

## 🎯 最新の実行方法（2025-08-04更新）

### 重要な変更点
1. **全ての実行は`entry_points/main.py`から行う**（プロジェクト方針）
2. **個別スケジューラーは廃止**（カタログベースに統合）
3. **時間精度付き予測**（日時まで保存されるように改善）

### クイックスタート
```bash
# 環境確認
python entry_points/main.py dev --check-env

# カタログ全銘柄解析（25銘柄を優先度順に）
python entry_points/main.py analyze ALL

# ダッシュボード確認
python entry_points/main.py dashboard --type main
```

---

*最終更新: 2025年8月4日*
*作成者: Claude Code (Anthropic)*