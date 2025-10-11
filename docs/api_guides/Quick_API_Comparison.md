# 金融データAPI 比較・推奨ガイド

## 🏆 総合推奨ランキング

| 順位 | API | 総合評価 | 推奨理由 |
|------|-----|----------|----------|
| 🥇 1位 | **FRED** | ⭐⭐⭐⭐⭐ | 完全無料、政府保証、最高信頼性 |
| 🥈 2位 | Alpha Vantage | ⭐⭐⭐⭐☆ | 無料プランあり、高品質データ |
| 🥉 3位 | Polygon.io | ⭐⭐⭐⭐☆ | 長期履歴、プロレベル |

---

## 📊 詳細比較表

### 費用・制限比較

| API | 無料プラン | 有料プラン | 日次制限 | 取得難易度 |
|-----|------------|------------|----------|------------|
| FRED | ✅ 完全無料 | なし | 17,280回/日 | ★☆☆ 超簡単 |
| Alpha Vantage | ✅ あり | $49.99/月 | 500回/日 | ★★☆ 簡単 |
| Polygon.io | ✅ あり | $99/月 | 300回/日 | ★★☆ 簡単 |
| Yahoo Finance | ✅ 無料 | なし | 不定 | ★★★ 困難 |

### データ品質・履歴比較

| API | S&P500履歴 | データ品質 | 安定性 | 1987年対応 |
|-----|------------|------------|--------|------------|
| FRED | 1957年〜 | 政府レベル | 極高 | ✅ 完全対応 |
| Alpha Vantage | 20年〜 | 高品質 | 高 | ✅ 対応 |
| Polygon.io | 15年〜 | 高品質 | 高 | ✅ 対応 |
| Yahoo Finance | 制限あり | 不安定 | 低 | ❌ 問題あり |

---

## 🎯 用途別推奨

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

## 💡 取得推奨順序

### 1. **FRED API**（必須・最優先）
- **取得時間**: 5分
- **費用**: 無料
- **必要性**: ★★★★★

**今すぐ取得する理由**:
- 本プロジェクトの中核データソース
- 1987年検証に必須
- 政府保証の最高品質

### 2. **Alpha Vantage API**（推奨・補完用）
- **取得時間**: 3分
- **費用**: 無料
- **必要性**: ★★★★☆

**取得する理由**:
- データ品質の相互検証
- より詳細な市場データ
- フォールバック機能

### 3. **Polygon.io API**（将来拡張用）
- **取得時間**: 5分
- **費用**: 無料〜有料
- **必要性**: ★★★☆☆

**将来的なメリット**:
- プロレベルの機能
- 長期履歴データ
- 商用利用対応

---

## 📋 APIキー取得チェックリスト

### ✅ FRED API（最優先）
- [ ] https://fred.stlouisfed.org/ でアカウント作成
- [ ] API Keys ページでキー取得
- [ ] 環境変数 `FRED_API_KEY` に設定
- [ ] 接続テスト実行
- [ ] 1987年データ取得確認

### ✅ Alpha Vantage API（推奨）
- [ ] https://www.alphavantage.co/support/#api-key でキー取得
- [ ] 環境変数 `ALPHA_VANTAGE_KEY` に設定
- [ ] 接続テスト実行
- [ ] SPYデータ取得確認

---

## 🎯 今日の推奨アクション

### **Step 1**: FRED APIキー取得（5分）
1. FRED公式サイトでアカウント作成
2. APIキー取得
3. 環境変数設定

### **Step 2**: 実市場データ検証実行（10分）
```bash
python tests/market_data/test_improved_market_validation.py
```

### **Step 3**: 1987年ブラックマンデー分析（結果確認）
- 論文値との比較
- フィッティング品質評価
- 実用性の検証

---

**次のアクションをお選びください**:
1. 🏛️ **FRED APIキー取得**（推奨）
2. 📊 **Alpha Vantage APIキー取得**（補完）
3. 🔬 **デモデータでの先行テスト**
4. 📚 **他のAPI調査継続**

*最終更新: 2025-08-01*