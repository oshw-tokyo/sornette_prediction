# 銘柄別可視化ダッシュボード - クイックスタートガイド

## 🎯 概要

銘柄別の詳細な可視化機能を提供する新しいダッシュボードを実装しました。

### 主な機能

1. **📈 価格チャート + 予測履歴**
   - 最新価格データと予測クラッシュ日時を重ね表示
   - 時系列でのグラデーション色付け
   - 時間精度での予測日時表示（散布図での重なり回避）

2. **📊 予測傾向散布図**
   - 分析日時 vs 予測日時の散布図
   - tc値の統計情報表示

3. **📋 パラメータ詳細**
   - 全パラメータの履歴テーブル
   - CSV出力機能

## 🚀 起動方法

### 方法1: 直接起動
```bash
./start_symbol_dashboard.sh
```

### 方法2: ランチャー経由
```bash
streamlit run src/web_interface/dashboard_launcher.py
```

### 方法3: Python直接実行
```bash
streamlit run src/web_interface/symbol_visualization_dashboard.py --server.port 8501
```

## 🎛️ 操作方法

### サイドバー設定

- **銘柄選択**: ドロップダウンから対象銘柄を選択
- **表示件数**: 予測履歴の表示数（5-50件）
- **価格データ期間**: 90日、180日、365日、730日から選択
- **表示間隔**: 全て、週次、隔週、月次（将来拡張用）

### タブ機能

1. **Price & Predictions**: 価格チャートと予測履歴
2. **Prediction Trend**: 予測傾向の散布図分析
3. **Parameters**: 詳細パラメータテーブル

## 🔧 技術仕様

### tc値の時間精度変換

```python
def tc_to_datetime_with_hours(tc, data_end_date, window_days):
    if tc > 1.0:
        days_beyond = (tc - 1.0) * window_days
        days_int = int(days_beyond)
        hours = (days_beyond - days_int) * 24
        return data_end_date + timedelta(days=days_int, hours=hours)
```

### ロバスト性対応

- データ欠損時のエラー処理
- 存在しない銘柄への対処
- 異常なtc値での安全な変換

## 📊 表示例

### 価格チャート
- 青線: 価格データ
- 赤い縦線（グラデーション）: 予測クラッシュ日時
- 薄い→濃い: 古い→新しい予測

### 散布図
- X軸: 分析実行日時
- Y軸: 予測クラッシュ日時
- 点の色: 時系列グラデーション

## ⚠️ 注意事項

1. **データ要件**: 
   - データベースに分析結果が必要
   - 先に分析実行: `python examples/basic_analysis.py`

2. **API制限**:
   - リアルタイム価格データはAPI制限により制限的
   - 週次更新スケジュール推奨

3. **表示制御のロバスト性**:
   - Issue I011として記録済み
   - データ欠損時の対処を今後改善予定

## 🧪 テスト実行

```bash
python test_symbol_dashboard.py
```

### テスト内容
- 基本機能テスト
- tc変換機能テスト
- データロバスト性テスト
- 異常値処理テスト

## 📋 今後の拡張予定

1. **予測履歴の時系列表示機能**: より詳細な時系列分析
2. **散布図による予測傾向分析**: 統計的分析機能
3. **複数銘柄比較機能**: Want要件として実装予定
4. **リアルタイムデータ更新**: スケジュール機能と連携

## 🔗 関連ファイル

- `src/web_interface/symbol_visualization_dashboard.py`: メインダッシュボード
- `src/web_interface/dashboard_launcher.py`: ランチャー
- `start_symbol_dashboard.sh`: 起動スクリプト
- `test_symbol_dashboard.py`: テストスクリプト

---

**実装完了日**: 2025-08-03  
**Issue対応**: I008（可視化要件不明確問題）を解決