# 🎯 LPPL分析ダッシュボード クイックスタート

## 🚀 ダッシュボード起動方法

### 方法1: 簡単起動スクリプト
```bash
./start_dashboard.sh
```

### 方法2: 直接起動
```bash
streamlit run src/web_interface/analysis_dashboard.py --server.headless=true --browser.gatherUsageStats=false
```

### 方法3: Streamlit初回設定後
```bash
streamlit run src/web_interface/analysis_dashboard.py
```

## 🌐 アクセス

ダッシュボード起動後、以下のURLにブラウザでアクセス：
- **ローカル**: http://localhost:8501
- **ネットワーク**: http://172.20.10.4:8501

## 📊 ダッシュボード機能

### 📈 Overview タブ
- 分析統計サマリー
- 品質分布チャート
- R²スコアトレンド

### 🔍 Analysis Results タブ
- 詳細分析結果一覧
- フィルター機能（銘柄・品質・期間）
- 個別分析詳細表示

### 📊 Visualizations タブ
- 保存済みチャート表示
- LPPL フィッティング結果
- 価格データとモデル比較

### ⚙️ Settings タブ
- データベース管理
- データエクスポート
- クリーンアップ機能

## 🔧 トラブルシューティング

### 初回起動時のメール入力
- Enterキーを押してスキップ可能
- または `--server.headless=true` オプション使用

### ポート8501が使用中の場合
```bash
streamlit run src/web_interface/analysis_dashboard.py --server.port=8502
```

### データベース確認
分析結果は以下に保存：
- `results/demo_analysis.db` - デモ用データベース
- `results/analysis_results.db` - 本番用データベース

## 📁 サンプルデータ

既に以下のサンプル分析が利用可能：
- NASDAQ分析結果（ID=1,2,3）
- R²スコア: ~0.857
- 品質: unstable（実データによる）

## 🎉 成功例

ダッシュボード正常動作確認済み：
✅ matplotlib GUIスタック問題解決  
✅ データベース永続化機能  
✅ ブラウザベース可視化  
✅ FRED API統合  