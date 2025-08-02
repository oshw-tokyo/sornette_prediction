# 統合API戦略・セットアップ・運用ガイド

## 概要

このドキュメントは、金融データ取得のための包括的なAPI戦略とセットアップガイドです。効率的なデータ取得から運用まで、すべての必要な情報を統合しています。

---

## 🏆 推奨API総合ランキング

| 順位 | API | 総合評価 | 推奨理由 | 主な用途 |
|------|-----|----------|----------|----------|
| 🥇 1位 | **FRED** | ⭐⭐⭐⭐⭐ | 完全無料、政府保証、最高信頼性 | 指数・経済指標 |
| 🥈 2位 | Alpha Vantage | ⭐⭐⭐⭐☆ | 無料プランあり、高品質データ | 個別株・詳細データ |
| 🥉 3位 | Polygon.io | ⭐⭐⭐⭐☆ | 長期履歴、プロレベル | 将来拡張用 |

---

## 📊 詳細API比較

### 費用・制限比較

| API | 無料プラン | 有料プラン | 日次制限 | 分間制限 | 取得難易度 |
|-----|------------|------------|----------|----------|------------|
| FRED | ✅ 完全無料 | なし | 17,280回/日 | 120回/分 | ★☆☆ 超簡単 |
| Alpha Vantage | ✅ あり | $49.99/月 | 500回/日 | 5回/分 | ★★☆ 簡単 |
| Polygon.io | ✅ あり | $99/月 | 300回/日 | - | ★★☆ 簡単 |
| Yahoo Finance | ✅ 無料 | なし | 不定 | 不定 | ★★★ 困難 |

### データ品質・履歴比較

| API | S&P500履歴 | データ品質 | 安定性 | 1987年対応 | 対応データ |
|-----|------------|------------|--------|------------|------------|
| FRED | 1957年〜 | 政府レベル | 極高 | ✅ 完全対応 | 指数・経済指標 |
| Alpha Vantage | 20年〜 | 高品質 | 高 | ✅ 対応 | 個別株・指数 |
| Polygon.io | 15年〜 | 高品質 | 高 | ✅ 対応 | 個別株・指数 |
| Yahoo Finance | 制限あり | 不安定 | 低 | ❌ 問題あり | 個別株・指数 |

---

## 🚀 FRED API セットアップ（最優先）

### 🏛️ FREDとは

**FRED (Federal Reserve Economic Data)** は、アメリカ連邦準備制度理事会（FRB）傘下のセントルイス連邦準備銀行が提供する経済データベースです。

#### 主な特徴
- **完全無料**: 個人・法人問わず無料利用可能
- **政府機関**: 連邦準備制度による高信頼性データ
- **豊富なデータ**: 80万以上の経済時系列データ
- **長期履歴**: 数十年にわたる歴史データ
- **API制限**: 120 requests/60秒（十分な制限）

### APIキー取得手順（5分で完了）

#### Step 1: FREDアカウント作成

1. **公式サイトにアクセス**
   ```
   https://fred.stlouisfed.org/
   ```

2. **右上の「My Account」をクリック**
   - 「Create new account」を選択

3. **基本情報を入力**
   ```
   Email: あなたのメールアドレス
   Password: 安全なパスワード
   First Name: 名前（英語）
   Last Name: 姓（英語）
   Organization: 個人なら「Individual」または「Personal」
   ```

4. **アカウント確認**
   - 入力したメールアドレスに確認メールが送信される
   - メール内のリンクをクリックしてアカウントを有効化

#### Step 2: APIキー取得

1. **API Keys ページに移動**
   ```
   直接アクセス: https://fred.stlouisfed.org/docs/api/api_key.html
   または: My Account → API Keys
   ```

2. **「Request API Key」をクリック**

3. **API キー情報を入力**
   ```
   Application Name: 「Stock Market Analysis」など
   Application URL: 空欄でも可（個人プロジェクトの場合）
   Application Description: 「Financial data analysis for research」など
   Organization: 「Individual」
   ```

4. **利用規約に同意して取得**
   - **即座にAPIキーが表示されます**
   - **32文字の英数字文字列**（例：a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6）

### APIキーの設定

#### 環境変数設定（推奨）

**macOS/Linux:**
```bash
# 一時的な設定
export FRED_API_KEY="your_api_key_here"

# 永続化（.bashrc または .zshrc に追加）
echo 'export FRED_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

**Windows:**
```cmd
# コマンドプロンプト
set FRED_API_KEY=your_api_key_here

# PowerShell
$env:FRED_API_KEY="your_api_key_here"

# 永続化（システム環境変数に追加）
setx FRED_API_KEY "your_api_key_here"
```

#### .envファイル設定
```bash
# .env ファイル
FRED_API_KEY=your_api_key_here
```

---

## 📱 Alpha Vantage API セットアップ（補完用）

### APIキー取得
1. https://www.alphavantage.co/support/#api-key でキー取得
2. 環境変数 `ALPHA_VANTAGE_KEY` に設定
3. 接続テスト実行

---

## 🎯 用途別推奨戦略

### 🔬 学術研究・論文検証用
**推奨**: **FRED API**
- 政府機関データによる最高の信頼性
- 査読論文での引用に適している
- 完全無料で長期利用可能

### 💼 商用・実トレーディング用
**推奨**: **Alpha Vantage Premium** または **Polygon.io**
- リアルタイムデータ
- 高頻度アクセス対応
- サポート充実

### 🎓 個人学習・プロトタイプ用
**推奨**: **FRED API** + **Alpha Vantage Free**
- 費用負担なし
- 十分な機能
- 段階的アップグレード可能

---

## 📈 効率的データ取得戦略

### 1. 優先順位ベースの取得

```
指数データ（NASDAQ, SP500等）
├── 1st: FRED（無料・高頻度）
└── 2nd: Alpha Vantage（バックアップ）

個別株データ（AAPL, MSFT等）
└── Alpha Vantageのみ（FREDはサポート外）
```

### 2. レート制限最適化

#### API制限詳細
- **FRED**: 120 requests/60秒（0.5秒間隔）、完全無料
- **Alpha Vantage**: 5 calls/分（12秒間隔）、500 calls/日

#### バッチ処理スケジュール
```
Phase 1: FRED指数データ取得（高速）
- 1分で最大120銘柄
- NASDAQ, SP500, DJIA, VIX等

Phase 2: Alpha Vantage個別株（慎重）
- 12秒間隔で順次取得
- 1時間で最大25銘柄
- 1日で最大500銘柄
```

#### 日次データ取得計画
```
Morning Batch (08:00)：
- FRED指数更新（5分）
- 重要個別株20銘柄（4分）

Evening Batch (18:00)：
- 残り個別株（1時間）
- 全体整合性チェック
```

### 3. データ保存・キャッシュ戦略

#### ローカルキャッシュ
- 取得データをローカルCSVで保存
- 日次差分更新のみ実行
- 過去データ再取得を回避

#### キャッシュ有効期限
```
リアルタイム分析：当日データのみ更新
週次分析：週末に過去1週間更新
月次分析：月末に過去1ヶ月更新
```

---

## 🔄 クラッシュ予測実行スケジュール

### 日次予測（平日）
```
06:00 - データ取得（指数）
07:00 - 指数LPPL分析実行
08:00 - レポート生成・アラート

18:00 - 個別株データ更新
19:00 - 個別株LPPL分析（重要銘柄のみ）
20:00 - 総合レポート更新
```

### 週次予測（日曜日）
```
Full Analysis Day：
- 全銘柄データ整合性チェック
- 長期ウィンドウLPPL分析
- 予測一貫性分析
- 包括的レポート生成
```

### 月次予測（月末）
```
Comprehensive Review：
- 全履歴データ検証
- パラメータ最適化
- モデル性能評価
- 戦略調整
```

---

## 📊 API使用量モニタリング

### 追跡指標
```python
# 例：daily_api_usage.json
{
    "date": "2025-08-02",
    "alpha_vantage": {
        "calls_used": 245,
        "calls_limit": 500,
        "remaining": 255
    },
    "fred": {
        "calls_used": 89,
        "calls_limit": "unlimited"
    }
}
```

### アラート設定
- Alpha Vantage使用量80%でアラート
- 使用量95%で非必須分析停止
- 制限到達で翌日まで待機

---

## 📋 利用可能な主要データシリーズ

| シリーズID | 名称 | 説明 | 開始年 | API |
|-----------|------|------|--------|-----|
| SP500 | S&P 500 | S&P500指数 | 1957 | FRED |
| DJIA | Dow Jones | ダウ工業株価平均 | 1896 | FRED |
| NASDAQCOM | NASDAQ | NASDAQ総合指数 | 1971 | FRED |
| VIXCLS | VIX | 恐怖指数 | 1990 | FRED |
| DGS10 | 10年債利回り | 米国10年国債利回り | 1962 | FRED |
| UNRATE | 失業率 | 米国失業率 | 1948 | FRED |
| CPIAUCSL | 消費者物価指数 | インフレ指標 | 1947 | FRED |

---

## 🧪 動作確認テスト

### FRED接続テスト
```python
#!/usr/bin/env python3
"""FRED API 動作確認テスト"""

import os
from src.data_sources.fred_data_client import FREDDataClient

def test_fred_connection():
    # APIキーの確認
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("❌ 環境変数 FRED_API_KEY が設定されていません")
        return False
    
    print(f"✅ APIキー確認: {api_key[:8]}...{api_key[-4:]}")
    
    # クライアント初期化
    client = FREDDataClient()
    
    # 接続テスト
    if client.test_connection():
        print("✅ FRED API接続成功")
        
        # S&P500データの取得テスト
        data = client.get_sp500_data("2023-01-01", "2023-12-31")
        if data is not None:
            print(f"✅ データ取得成功: {len(data)}日分")
            print(f"   期間: {data.index[0]} - {data.index[-1]}")
            return True
    
    print("❌ FRED API接続失敗")
    return False

if __name__ == "__main__":
    test_fred_connection()
```

---

## 🚀 実装優先順位

### Phase 1: FRED API実装（推奨開始点）
```python
from src.data_sources.fred_data_client import FREDDataClient

client = FREDDataClient()
data = client.get_sp500_data("1985-01-01", "1987-10-31")
```

**メリット**:
- 5分で利用開始可能
- 政府データの最高信頼性
- 1987年データの完全再現

### Phase 2: Alpha Vantage統合（品質向上）
```python
from src.data_sources.alpha_vantage_client import AlphaVantageClient

client = AlphaVantageClient()
data = client.get_1987_black_monday_data()
```

**メリット**:
- データ品質の相互検証
- より詳細な株価情報（OHLCV）
- 無料プランで十分

### Phase 3: 統合システム（本格運用）
```python
from src.data_sources.unified_data_client import UnifiedDataClient

client = UnifiedDataClient()
data, source = client.get_sp500_historical_data("1985-01-01", "1987-10-31")
```

**メリット**:
- 自動フォールバック
- 最高の可用性
- 複数ソース検証

---

## 💰 費用対効果分析

### 無料プラン継続案
- **メリット**: 完全無料
- **制約**: 個別株25銘柄/日限定
- **適用**: 小規模・研究用途

### 有料プラン検討案
- **費用**: $49.99/月（Alpha Vantage）
- **メリット**: 制限大幅緩和、リアルタイム分析可能
- **ROI**: 商用利用時に検討

---

## 🛡️ セキュリティとベストプラクティス

### ✅ 推奨事項
- APIキーを環境変数で管理
- GitリポジトリにAPIキーを含めない
- `.env` ファイルを `.gitignore` に追加
- 定期的にAPIキーを更新

### ❌ 避けるべき事項
- APIキーをソースコードに直接記述
- APIキーを公開リポジトリにコミット
- 他人とAPIキーを共有

### セキュリティ設定例
```bash
# .gitignore に追加
.env
*.key
config/secrets.py
```

---

## 🆘 緊急時対応計画

### API制限到達時
1. FRED指数データのみで継続
2. 重要個別株のみ選択分析
3. 翌日まで待機・履歴分析に切替

### API障害時
1. キャッシュデータで継続
2. 手動データ補完
3. 代替API検討（Polygon等）

---

## 💡 トラブルシューティング

### よくある問題と解決方法

#### 1. APIキーが認識されない
```bash
# 環境変数の確認
echo $FRED_API_KEY  # Linux/macOS
echo %FRED_API_KEY% # Windows
```

#### 2. レート制限エラー
```
Error: API request limit reached
```
**解決策**: 指定の制限内でリクエスト間隔を調整

#### 3. データが見つからない
```
Error: Series not found
```
**解決策**: シリーズIDを確認（SP500, DJIA, NASDAQCOM など）

---

## ✅ APIキー取得チェックリスト

### FRED API（最優先）
- [ ] https://fred.stlouisfed.org/ でアカウント作成
- [ ] API Keys ページでキー取得
- [ ] 環境変数 `FRED_API_KEY` に設定
- [ ] 接続テスト実行
- [ ] 1987年データ取得確認

### Alpha Vantage API（推奨）
- [ ] https://www.alphavantage.co/support/#api-key でキー取得
- [ ] 環境変数 `ALPHA_VANTAGE_KEY` に設定
- [ ] 接続テスト実行
- [ ] SPYデータ取得確認

---

## 📞 サポートと追加情報

### 公式リソース
- **FRED ホームページ**: https://fred.stlouisfed.org/
- **FRED API ドキュメント**: https://fred.stlouisfed.org/docs/api/
- **Alpha Vantage**: https://www.alphavantage.co/
- **データシリーズ検索**: https://fred.stlouisfed.org/search/

---

## 🎯 結論

現在の無料プランでも効率的な運用は可能。重要なのは：

1. **指数優先**: FRED活用で基本指標を高頻度監視
2. **個別株選択**: 重要銘柄に絞った集中分析  
3. **キャッシュ活用**: 過去データ再取得回避
4. **スケジュール最適化**: レート制限内での最大効率

商用展開時は有料プラン移行を検討。

---

*最終更新: 2025-08-02*
*統合・作成者: Claude Code*