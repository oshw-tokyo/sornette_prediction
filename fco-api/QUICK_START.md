# FCO v2.1 FastAPI クイックスタートガイド

このファイルは開発途中に利用するための一時的なものです。

## 🚀 動作確認手順

### 1. テストデータの生成（初回のみ）
```bash
cd workspace_for_claude
python generate_fco_test_data.py
```
これにより、SP500、NASDAQCOM、BTCの3銘柄×157件ずつのテストデータが生成されます。

### 2. FastAPIサーバーの起動
```bash
cd fco-api
uvicorn app.main:app --reload --port 8000
```

### 3. ブラウザでの確認

#### A. HTMLダッシュボード
```
http://localhost:8000/dashboard
```
- ドロップダウンから銘柄を選択
- "Load Data"ボタンをクリック
- 3つのタブでデータを確認：
  - Time Series: 時系列グラフ
  - Analysis Details: 最新分析の詳細
  - Historical Data: 履歴データ（CSV出力可能）

#### B. API ドキュメント（Swagger UI）
```
http://localhost:8000/docs
```
- インタラクティブなAPI仕様書
- 各エンドポイントをブラウザから直接テスト可能

#### C. 個別APIエンドポイントのテスト
```bash
# 利用可能な銘柄一覧
curl http://localhost:8000/api/v1/fco/symbols

# 特定銘柄の最新分析
curl http://localhost:8000/api/v1/fco/symbols/SP500/latest

# 特定銘柄のサマリー
curl http://localhost:8000/api/v1/fco/symbols/SP500/summary

# 時系列データ
curl http://localhost:8000/api/v1/fco/symbols/SP500/timeseries
```

## 📊 確認ポイント

1. **ダッシュボード表示**
   - グラデーションヘッダーが表示される
   - 銘柄選択が動作する
   - グラフが正しく描画される

2. **データ取得**
   - DS-LPPLS Confidence値が表示される
   - Bubble Type（positive/negative）が表示される
   - Predicted Critical Timeが表示される

3. **インタラクティブ機能**
   - タブ切り替えが動作する
   - CSVエクスポートが動作する
   - エラー/成功メッセージが表示される

## 🛠️ トラブルシューティング

### ポート8000が使用中の場合
```bash
# 別のポートで起動
uvicorn app.main:app --reload --port 8001
```

### データが表示されない場合
```bash
# データベースの確認
ls -la results/fco_analysis_results.db

# テストデータの再生成
cd workspace_for_claude
python generate_fco_test_data.py
```

### モジュールエラーの場合
```bash
# 依存関係のインストール
cd fco-api
pip install -r requirements.txt
```

## 📝 注意事項

- 現在はテストデータでの動作確認用
- 実際のFCOエンジンは未実装（Phase 2以降で対応）
- 認証機能は未実装（後回し）