# 安定版v1.0 統合ナレッジベース

**作成日**: 2025-08-10  
**バージョン**: v1.0-stable  
**目的**: 安定版実装に関する全知識の統合・整理

## 🎯 安定版v1.0 実装方針

### 基本戦略
**FRED優先原則 + Twelve Data補完** による高品質データ取得システムの実現

### データソース構成
- **FRED**: 24銘柄（経済指標14 + 株式指数10）- 制限なし・最高品質・政府公式
- **Twelve Data**: 56銘柄（仮想通貨36 + 個別株式20）- 800req/日・高品質API

### 総対象銘柄: 80銘柄

## 📊 詳細銘柄配分

### FRED担当（24銘柄）- 既存維持
#### 経済指標（14銘柄）
```
金利: DGS2, DGS10, DGS30, DFF
物価: CPIAUCSL, CPILFESL
原油: DCOILWTICO, DCOILBRENTEU
為替: DEXJPUS, DEXUSEU, DEXUSUK
その他: VIXCLS, GOLDAMGBD228NLBM, CBBTCUSD
```

#### 株式指数（10銘柄）
```
主要指数: SP500, NASDAQCOM, DJIA
セクター指数: DJTA, DJUA, NASDAQ100, NASDAQBANK, NASDAQFIN, NASDAQSOX, NASDAQTRAN
```

### Twelve Data担当（56銘柄）- 新規追加
#### 仮想通貨（36銘柄）
**Tier 1（基軸・10銘柄）**: BTC, ETH, BNB, XRP, SOL, USDC, USDT, ADA, AVAX, DOT  
**Tier 2（DeFi・10銘柄）**: LINK, MATIC, UNI, LTC, ATOM, ALGO, VET, FIL, AAVE, CRV  
**Tier 3（その他・16銘柄）**: DOGE, SHIB, SAND, MANA, AXS, ENJ, COMP, SUSHI, 1INCH, BAT, XMR, ZEC, DASH, EOS, TRX, XTZ

#### 個別株式（20銘柄）
**Tech（8銘柄）**: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, NFLX  
**Finance（4銘柄）**: JPM, BAC, WFC, GS  
**Others（8銘柄）**: WMT, XOM, JNJ, PG, V, MA, DIS, MCD

## ⚠️ 廃止API・理由

### CoinGecko - 制限・設定複雑性
- **制限**: 10req/分（厳しすぎる）
- **問題**: 大文字小文字ID変更問題（BTC→bitcoin）
- **影響**: 全35銘柄で設定エラー頻発

### Alpha Vantage - 制限・品質問題
- **制限**: 500req/日（中程度だが不安定）
- **問題**: データ品質にばらつき・エラー率高い
- **影響**: 株式データの信頼性に懸念

### Finnhub - 時系列制限（Issue I051）
- **致命的制限**: 過去データ取得不可（403エラー）
- **LPPL分析**: 365日データ必須だが無料プランでは不可
- **評価**: 技術実装は正常だが分析価値限定的

## 🔧 技術実装詳細

### 1. FRED優先ロジック
```python
# 統合クライアントでの優先順位制御
def get_symbol_data(symbol):
    fred_symbols = ['SP500', 'NASDAQCOM', 'CBBTCUSD', ...]
    if symbol in fred_symbols:
        return fred_client.get_data(symbol)  # FRED最優先
    else:
        return twelvedata_client.get_data(symbol)  # Twelve Data使用
```

### 2. カタログベース管理
- **重複処理**: CBBTCUSD（FRED優先）vs BTC（Twelve Data）
- **メタデータ**: evaluation_score, category, data_sources
- **統一管理**: market_data_catalog.json に80銘柄集約

### 3. API制限最適化
- **FRED**: 無制限・政府公式・最高品質
- **Twelve Data**: 800req/日 → 実使用57req/日（制限内）
- **レート管理**: 120秒間隔で安全な取得ペース

## 📋 実装チェックリスト

### 完了済み
- [x] **ドキュメント更新**: CLAUDE.md, README.md, implementation_strategy.md
- [x] **進捗管理更新**: CURRENT_PROGRESS.md, CURRENT_ISSUES.md
- [x] **古い情報整理**: 廃止API情報のアーカイブ・ナレッジ統合

### 実装予定
- [ ] **カタログ更新**: market_data_catalog.json（80銘柄構成）
- [ ] **統合クライアント修正**: FRED優先ロジック実装
- [ ] **主要銘柄テスト**: BTC・ETH・AAPL・SP500動作確認
- [ ] **論文再現保護**: 1987年100/100スコア維持確認
- [ ] **初回データ取得**: backfill実行（80銘柄×365日）

## 🎯 期待される成果

### システム性能向上
- **データ取得率**: 95%以上（80銘柄中76銘柄以上）
- **APIエラー率**: 5%以下（高品質API使用）
- **分析速度**: 大幅向上（待機時間短縮）

### 予測精度向上
- **包括的データ**: 80銘柄による多角的市場分析
- **高品質データ**: FRED・Twelve Dataの信頼性
- **時系列一貫性**: 単一APIによるデータ整合性

### 運用安定性
- **API制限**: 大幅改善（10req/分 → 800req/日）
- **エラー耐性**: 高品質APIによる信頼性向上
- **保守性**: 2つのAPIのみでシンプル構成

## 🚨 重要な注意事項

### 論文再現保護（最重要）
```bash
# すべての変更前後で必ず実行
python entry_points/main.py validate --crash 1987
# 期待結果: 100/100スコア維持必須
```

### データソース優先順位（厳守）
1. **FRED最優先** - 政府公式・無制限・既存実績
2. **Twelve Data補完** - FRED不在銘柄のみ使用
3. **重複時はFRED** - CBBTCUSD vs BTC の例

### API制限管理（継続監視）
- **Twelve Data**: 800req/日制限の遵守
- **実使用量**: 57req/日（余裕あり）
- **レート制限**: 120秒間隔維持

## 📅 実装タイムライン

### Day 1-2: システム更新
- カタログ構築（80銘柄）
- 統合クライアント修正（FRED優先）
- 主要銘柄テスト

### Day 3-4: 検証・テスト
- データ取得品質確認
- API制限動作確認
- 論文再現テスト

### Day 5: 運用開始
- 初回データ取得（backfill）
- ダッシュボード確認
- 安定版リリース

## 🏆 成功基準

### 必須達成項目
- [ ] 80銘柄カタログ完成
- [ ] FRED優先ロジック実装
- [ ] 論文再現100/100維持
- [ ] 主要銘柄データ取得成功

### 品質指標
- データ取得成功率: ≥95%
- APIエラー率: ≤5%
- システム応答時間: ≤2分（365日データ）
- 予測精度: 現行レベル以上維持

---

**策定者**: Claude Code  
**承認**: プロジェクトオーナー  
**実装責任**: 安定版v1.0開発チーム  
**管理**: docs/progress_management/ システム

*本ナレッジベースは安定版v1.0実装の完了まで継続更新されます。*