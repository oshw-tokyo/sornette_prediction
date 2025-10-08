# FCO日次分析スケジューラー使用ガイド

## 概要

FCO日次分析スケジューラーは、ETH Zurich FCO方式の多重時間窓LPPLS分析を日次で実行するシステムです。126個の時間窓を使用してDS-LPPLS Confidence指標を計算し、市場のバブル状態を継続的に監視します。

## 主な特徴

- **日次実行**: 毎日最新のデータで分析を実行（LPPL日次分析とは独立）
- **包括的分析**: カタログ全81銘柄を自動分析
- **FCO準拠**: 126時間窓（125-750日）での多重分析
- **データベース保存**: 全窓結果とConfidence履歴を保存
- **エラー耐性**: 一部銘柄が失敗しても他は継続

## コマンド一覧

### 1. 日次分析の実行

```bash
# 全銘柄（81銘柄）の分析を実行
python entry_points/main.py fco-daily run
```

### 2. 失敗銘柄の再実行

```bash
# 前回失敗した銘柄のみ再実行
python entry_points/main.py fco-daily retry
```

### 3. 状態確認

```bash
# スケジューラーの現在状態を確認
python entry_points/main.py fco-daily status
```

出力例：
```json
{
  "configured_symbols": 81,
  "last_run": "2025-09-13",
  "last_success": 78,
  "last_failure": 3,
  "failed_symbols": ["SYMBOL1", "SYMBOL2", "SYMBOL3"],
  "high_confidence_bubbles": [
    {
      "symbol": "SP500",
      "ds_lppls_confidence": 0.6,
      "bubble_type": "positive_bubble"
    }
  ]
}
```

### 4. テスト実行（3銘柄のみ）

```bash
# SP500, NASDAQCOM, DJIAのみでテスト
python entry_points/main.py fco-daily test
```

## データ保存

### データベース構造

分析結果は`results/fco_analysis_results.db`に保存されます：

1. **fco_analysis_results**: メイン分析結果
   - symbol: 銘柄コード
   - analysis_basis_date: 分析基準日
   - ds_lppls_confidence: 正のバブル信頼度
   - ds_lppls_confidence_neg: 負のバブル信頼度
   - bubble_type: バブルタイプ分類
   - predicted_tc: 予測臨界時間
   - scenario_probability: シナリオ確率

2. **fco_window_fits**: 全126窓の詳細結果
   - analysis_id: 分析ID（親テーブル参照）
   - window_size: 窓サイズ（日数）
   - t_c: 臨界時間
   - m, omega, damping: LPPLSパラメータ
   - r_squared: 決定係数
   - is_qualified: 品質基準合格フラグ

3. **fco_confidence_history**: Confidence時系列履歴
   - symbol: 銘柄コード
   - timestamp: 記録時刻
   - confidence: DS-LPPLS Confidence値
   - bubble_status: バブル状態

### 状態管理

スケジューラーの状態は`results/fco_scheduler_state.json`に保存されます：

```json
{
  "last_run_date": "2025-09-13",
  "last_success_count": 78,
  "last_failure_count": 3,
  "failed_symbols": ["SYMBOL1", "SYMBOL2"]
}
```

## 定期実行の設定

### cronジョブの設定例

毎日午前9時に実行する場合：

```bash
# crontabを編集
crontab -e

# 以下を追加
0 9 * * * cd /path/to/sornette_prediction && python entry_points/main.py fco-daily run >> logs/fco_daily.log 2>&1
```

### systemdタイマーの設定例

より高度な管理が必要な場合：

1. サービスファイル作成 (`/etc/systemd/system/fco-daily.service`)
```ini
[Unit]
Description=FCO Daily Analysis
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/sornette_prediction
ExecStart=/usr/bin/python3 entry_points/main.py fco-daily run
User=your-user
StandardOutput=append:/path/to/logs/fco_daily.log
StandardError=append:/path/to/logs/fco_daily_error.log
```

2. タイマーファイル作成 (`/etc/systemd/system/fco-daily.timer`)
```ini
[Unit]
Description=FCO Daily Analysis Timer
Requires=fco-daily.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

3. タイマー有効化
```bash
sudo systemctl enable fco-daily.timer
sudo systemctl start fco-daily.timer
```

## エラー処理

### 失敗銘柄の再実行

分析が失敗した銘柄は自動的に記録され、`retry`コマンドで再実行できます：

```bash
# 状態確認
python entry_points/main.py fco-daily status

# 失敗銘柄のみ再実行
python entry_points/main.py fco-daily retry
```

### API制限への対応

- 各銘柄の分析後に0.5秒の待機時間
- API制限エラー時は自動的にスキップ
- 失敗銘柄は後で再実行可能

## ダッシュボードでの確認

FCO分析結果はダッシュボードの「FCO Analysis」タブで確認できます：

```bash
python entry_points/main.py dashboard
```

表示内容：
- DS-LPPLS Confidence推移グラフ
- 時間窓分析の詳細
- バブル状態の判定
- 統計情報とメタデータ

## トラブルシューティング

### よくある問題と解決策

1. **「本日は既に実行済み」エラー**
   - 状態ファイルをリセット: `rm results/fco_scheduler_state.json`

2. **API認証エラー**
   - `.env`ファイルの設定を確認
   - 必要なAPIキーが設定されているか確認

3. **データ取得エラー**
   - ネットワーク接続を確認
   - APIの稼働状況を確認
   - `retry`コマンドで再実行

4. **分析エラー**
   - データ期間が短すぎる可能性（最低750日必要）
   - ログファイルで詳細を確認

## 設計思想

### シンプルさ優先

- 複雑な設定管理を避ける
- 日次実行に特化
- FCOエンジンとの疎結合
- エラー時の継続性

### LPPL分析との独立性

- 完全に独立したデータベース
- 独立したスケジューラー
- 独立したダッシュボード表示
- 異なる実行頻度（日次 vs 週次）

## 関連ファイル

- **スケジューラー本体**: `applications/analysis_tools/fco_daily_scheduler.py`
- **FCOエンジン**: `core/fitting/fco_engine.py`
- **データベース管理**: `infrastructure/database/fco_results_database.py`
- **エントリーポイント**: `entry_points/main.py`
- **状態ファイル**: `results/fco_scheduler_state.json`
- **データベース**: `results/fco_analysis_results.db`