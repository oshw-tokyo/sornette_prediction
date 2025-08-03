# データソース戦略 - FRED vs Alpha Vantage 役割分担

## 📊 データソース最適化戦略

### **基本方針**: 各APIの特性を活かした適材適所の活用

## 🏛️ FRED API - 政府系指数データ

### **対象データ**:
- **NASDAQ Composite**: `NASDAQCOM`
- **S&P 500**: `SP500`  
- **Dow Jones**: `DJIA`
- **VIX**: `VIXCLS`

### **特徴・利点**:
- ✅ **政府機関データ**: 高い信頼性と正確性
- ✅ **無料大容量**: 120 requests/分の十分な制限
- ✅ **長期履歴**: 数十年分のデータ利用可能
- ✅ **安定性**: 政府系のため継続性が高い

### **実装例**:
```python
# scheduled_nasdaq_analysis.py
symbol = "NASDAQCOM"  # FRED専用
data_source = "fred"
window_days = 365     # 1年間データ
delay_seconds = 0.5   # 緩い制限対応
```

## 🏢 Alpha Vantage API - 個別株式データ

### **対象データ**:
- **Apple Inc.**: `AAPL`
- **Microsoft**: `MSFT`
- **Google**: `GOOGL`
- **Amazon**: `AMZN`
- **Tesla**: `TSLA`
- **NVIDIA**: `NVDA`

### **特徴・制約**:
- ✅ **個別株式**: FREDでは取得不可の銘柄データ
- ✅ **リアルタイム性**: 最新の株価情報
- ⚠️ **厳格制限**: 75 calls/日, 5 calls/分
- ⚠️ **個別株変動**: より複雑なパターン分析が必要

### **実装例**:
```python
# scheduled_aapl_analysis.py
symbol = "AAPL"              # Alpha Vantage専用
data_source = "alpha_vantage"
window_days = 730            # 2年間データ（個別株は長期必要）
delay_seconds = 12           # 厳格制限対応
attempts = 15                # 多めの試行回数
```

## 🎯 選定ターゲット: AAPL (Apple Inc.)

### **選定理由**:

1. **技術的理由**:
   - FREDでは絶対に取得できない個別株式
   - Alpha Vantageでのみ利用可能
   - 重複の無駄を完全排除

2. **分析価値**:
   - **世界最大の時価総額**: 市場全体への影響力
   - **高流動性**: 信頼性の高いLPPL分析が可能
   - **バブル傾向**: IT・成長株特有のパターン
   - **長期データ**: 十分な歴史的データ

3. **戦略的意義**:
   - **指数 vs 個別株**: NASDAQ(指数)とAAPL(個別株)の比較分析
   - **データソース検証**: 各APIの特性把握
   - **スケーラビリティ**: 他の個別株への展開基盤

## 📈 分析アプローチの違い

| 項目 | FRED (NASDAQ) | Alpha Vantage (AAPL) |
|------|---------------|----------------------|
| **データ期間** | 365日 (1年) | 730日 (2年) |
| **フィッティング試行** | 10回 | 15回 |
| **API待機時間** | 5秒 | 12秒 |
| **分析頻度** | 週次 | 週次 |
| **期待パターン** | 指数レベルのマクロトレンド | 個別株の成長・調整サイクル |

## 🔄 将来の拡張計画

### **Phase 1** (現在):
- NASDAQ (FRED) + AAPL (Alpha Vantage)
- 基本的な役割分担確立

### **Phase 2**:
- FRED: S&P500, DJIA, VIX 追加
- Alpha Vantage: MSFT, GOOGL, AMZN 追加

### **Phase 3**:
- セクター別分析（テック、金融、ヘルスケア）
- 国際市場への展開

## 📋 データソース管理要件（2025-08-03追加）

### **🎯 基本原則**

#### **1. API制限・安定性優先の選択**
- ✅ **FRED API優先**: 120 calls/分の十分な制限、政府機関の安定性
- ⚠️ **Alpha Vantage**: 75 calls/日、5 calls/分の厳格制限下でのみ使用
- 📊 **自動判断**: API制限に余裕があり安定したサービスを優先選択

#### **2. 重複取得の厳格回避**
- 🚫 **完全排他制御**: 同一銘柄で複数APIからの取得禁止
- 📝 **一意対応**: 各銘柄は1つのAPIのみからデータ取得
- 🔄 **フォールバック**: 主要APIが失敗時のみ代替API使用

#### **3. メタ情報の透明化**
- 🎛️ **銘柄ベース選択**: インデックス・個別株での統一フィルタリング
- 📊 **データソース表示**: 選択後に取得元API・最終更新日時を表示
- 🔍 **品質情報**: データ点数・期間・信頼性レベルの可視化

### **🏗️ 実装要件**

#### **A. 銘柄・APIマッピングシステム**
```yaml
# 要求仕様: 集中管理設定ファイル
symbol_mapping.yaml:
  indices:
    NASDAQ: {primary: FRED, secondary: null, symbol_mapping: {FRED: NASDAQCOM}}
    SP500: {primary: FRED, secondary: Alpha_Vantage, symbol_mapping: {FRED: SP500, Alpha_Vantage: SPY}}
    
  individual_stocks:
    AAPL: {primary: Alpha_Vantage, secondary: null, symbol_mapping: {Alpha_Vantage: AAPL}}
    MSFT: {primary: Alpha_Vantage, secondary: null, symbol_mapping: {Alpha_Vantage: MSFT}}
```

#### **B. 動的データソース選択**
```python
# 要求仕様: インテリジェントソース選択
class SmartDataSourceSelector:
    def select_optimal_source(self, symbol: str) -> str:
        # 1. API制限状況の確認
        # 2. データ品質・鮮度の評価  
        # 3. 安定性スコアに基づく選択
        # 4. 重複回避チェック
        pass
```

#### **C. ダッシュボードメタ情報表示**
```python
# 要求仕様: 選択後メタ情報表示
Dashboard Components:
  - Symbol Selector (dropdown)
  - Data Source Info Panel:
    ├── API Provider: "FRED" 
    ├── Last Updated: "2025-08-03 15:30"
    ├── Data Points: "249 days"
    ├── Reliability: "⭐⭐⭐⭐⭐ (Government)"
    └── Update Frequency: "Daily"
```

### **⚠️ 重要な注意事項**

### **API制限管理**:
1. **Alpha Vantage**: 日次75回制限の厳格管理
2. **実行間隔**: 12秒以上の間隔必須
3. **エラー監視**: 制限超過時の適切な処理

### **データ品質**:
1. **個別株**: より多くのノイズとボラティリティ
2. **フィッティング**: 指数より多くの試行が必要
3. **検証**: 各データソースの特性を考慮した評価

## 📋 実行ガイド

### **NASDAQ解析** (FRED):
```bash
python scheduled_nasdaq_analysis.py
```

### **AAPL解析** (Alpha Vantage):
```bash
python scheduled_aapl_analysis.py
```

### **統合ダッシュボード**:
```bash
./start_symbol_dashboard.sh
# ブラウザ: http://localhost:8501
# 銘柄選択: NASDAQCOM / AAPL
```

## 🎯 期待される成果

1. **役割分担の最適化**: 各APIの強みを最大限活用
2. **分析精度の向上**: 適切なデータ期間と試行回数
3. **コスト効率**: API制限内での最大パフォーマンス
4. **比較分析**: 指数と個別株の予測パターン比較
5. **スケーラビリティ**: 他銘柄への拡張基盤

---

**作成日**: 2025-08-03  
**責任者**: プロジェクトオーナー  
**更新**: API制限・データ品質の実証結果に基づく随時更新