# 🎯 API優先順位マトリックス - 実運用ガイド

## 📋 概要

このドキュメントは、データ取得時の実際の優先順位判定とAPI選択戦略を定義します。

---

## 🏆 API優先順位ランキング

### ランキング基準
1. **コスト効率** (無料 > 安価 > 高額)
2. **レート制限** (緩い > 厳しい)
3. **データ品質** (公的機関 > 商業 > 集約)
4. **カバレッジ** (広範囲 > 専門特化)

### 総合ランキング
| 順位 | API | スコア | コスト | 制限 | 品質 | 特化領域 |
|-----|-----|--------|--------|------|------|----------|
| 🥇 | **FRED** | 95/100 | 無料 | 10,000/日 | 最高 | 米国指数・経済指標 |
| 🥈 | **Alpha Vantage** | 70/100 | 無料制限あり | 500/日 | 良質 | 個別株式 |
| 🥉 | **CoinGecko** | 65/100 | 無料制限厳 | 20/分 | 中程度 | 仮想通貨 |

---

## 📊 銘柄別API優先順位マトリックス

### 🏅 Tier 1: FRED優先銘柄（コア資産）
| 銘柄コード | 表示名 | 1st API | 2nd API | 3rd API | 取得確度 |
|-----------|-------|---------|---------|---------|----------|
| **NASDAQCOM** | NASDAQ Composite | 🥇 FRED | 🥈 Alpha Vantage | - | 99% |
| **SP500** | S&P 500 Index | 🥇 FRED | 🥈 Alpha Vantage | - | 99% |
| **NASDAQ100** | NASDAQ 100 Index | 🥇 FRED | - | - | 95% |
| **DJIA** | Dow Jones Industrial | 🥇 FRED | 🥈 Alpha Vantage | - | 99% |
| **CBBTCUSD** | Bitcoin (FRED) | 🥇 FRED | 🥉 CoinGecko | - | 99% |
| **CBETHUSD** | Ethereum (FRED) | 🥇 FRED | 🥉 CoinGecko | - | 99% |

### 🏅 Tier 2: セクター・専門指数
| 銘柄コード | 表示名 | 1st API | 2nd API | 3rd API | 取得確度 |
|-----------|-------|---------|---------|---------|----------|
| **NASDAQSOX** | Semiconductor Index | 🥇 FRED | - | - | 90% |
| **NASDAQRSBLCN** | Blockchain Index | 🥇 FRED | - | - | 85% |
| **DJTA** | Transportation Average | 🥇 FRED | - | - | 90% |
| **DJUA** | Utility Average | 🥇 FRED | - | - | 90% |
| **VIXCLS** | VIX Index | 🥇 FRED | 🥈 Alpha Vantage | - | 95% |
| **GVZCLS** | Gold Volatility | 🥇 FRED | - | - | 85% |
| **OVXCLS** | Oil Volatility | 🥇 FRED | - | - | 85% |

### 🏅 Tier 3: 仮想通貨拡張
| 銘柄コード | 表示名 | 1st API | 2nd API | 3rd API | 取得確度 |
|-----------|-------|---------|---------|---------|----------|
| **BNB** | Binance Coin | 🥉 CoinGecko | - | - | 80% |
| **SOL** | Solana | 🥉 CoinGecko | - | - | 80% |
| **ADA** | Cardano | 🥉 CoinGecko | - | - | 80% |
| **DOGE** | Dogecoin | 🥉 CoinGecko | - | - | 75% |

### 🏅 Tier 4: 個別株式
| 銘柄コード | 表示名 | 1st API | 2nd API | 3rd API | 取得確度 |
|-----------|-------|---------|---------|---------|----------|
| **AAPL** | Apple Inc. | 🥈 Alpha Vantage | - | - | 85% |
| **TSLA** | Tesla Inc. | 🥈 Alpha Vantage | - | - | 85% |

### 🏅 Tier 5: 補助指標
| 銘柄コード | 表示名 | 1st API | 2nd API | 3rd API | 取得確度 |
|-----------|-------|---------|---------|---------|----------|
| **REITTMA** | REIT Mortgage Assets | 🥇 FRED | - | - | 90% |

---

## ⚡ 実行効率最適化

### 実行プロファイル別推奨
```python
# Profile A: 高速実行（FRED中心）
tier1_symbols = [
    'CBBTCUSD', 'NASDAQCOM', 'SP500', 'NASDAQ100', 'DJIA'
]
実行時間 = "約2-3分"
成功率 = "98%"

# Profile B: バランス実行（FRED + CoinGecko）
tier1_2_symbols = [
    'CBBTCUSD', 'CBETHUSD', 'NASDAQCOM', 'SP500', 
    'NASDAQSOX', 'BNB', 'SOL', 'ADA'
]
実行時間 = "約8-12分"
成功率 = "85%"

# Profile C: 完全実行（全API）
all_symbols = "全20銘柄"
実行時間 = "約20-30分"
成功率 = "78%"
```

---

## 🎯 戦略的実装パターン

### パターン1: コストパフォーマンス最優先
```python
実行順序 = [
    "FRED銘柄 → 即座実行（制限なし）",
    "CoinGecko銘柄 → 3秒間隔実行", 
    "Alpha Vantage銘柄 → 12秒間隔実行"
]
推奨用途 = "日次自動実行"
```

### パターン2: データ網羅性優先
```python
実行順序 = [
    "Tier1-2 (FRED) → 優先実行",
    "Tier3 (CoinGecko) → 補完実行",
    "Tier4 (Alpha Vantage) → 最終実行"
]
推奨用途 = "週次包括分析"
```

### パターン3: リアルタイム性優先
```python
実行順序 = [
    "高変動銘柄優先 → BTC, ETH, SOL",
    "市場指数補完 → NASDAQ, S&P500",
    "個別株限定実行 → AAPL, TSLA"
]
推奨用途 = "市場監視"
```

---

## 📈 取得成功率予測

### 銘柄群別成功率
| 銘柄群 | 含有銘柄数 | 予想成功率 | 実行時間 | 制限要因 |
|--------|-----------|-----------|----------|----------|
| **Tier 1 (FRED)** | 6銘柄 | 98% | 3分 | なし |
| **Tier 2 (FRED)** | 7銘柄 | 90% | 4分 | なし |
| **Tier 3 (CoinGecko)** | 4銘柄 | 80% | 15分 | レート制限 |
| **Tier 4 (Alpha Vantage)** | 2銘柄 | 85% | 25秒 | レート制限 |
| **全体** | 20銘柄 | 87% | 25分 | 混合 |

### 時間帯別推奨
```python
最適実行時間帯 = {
    "FRED": "24時間対応（制限なし）",
    "Alpha Vantage": "米国市場時間外推奨",
    "CoinGecko": "アジア時間帯（負荷軽減期）"
}
```

---

## 🛠️ 実装コード例

### 優先順位実装
```python
def get_api_priority(symbol: str) -> List[str]:
    """銘柄に対するAPI優先順位を返す"""
    
    tier1_fred = ['NASDAQCOM', 'SP500', 'NASDAQ100', 'DJIA', 'CBBTCUSD', 'CBETHUSD']
    tier2_fred = ['NASDAQSOX', 'NASDAQRSBLCN', 'DJTA', 'DJUA', 'VIXCLS', 'GVZCLS', 'OVXCLS', 'REITTMA']
    tier3_coingecko = ['BNB', 'SOL', 'ADA', 'DOGE']
    tier4_alpha = ['AAPL', 'TSLA']
    
    if symbol in tier1_fred or symbol in tier2_fred:
        return ['fred', 'alpha_vantage', 'coingecko']
    elif symbol in tier3_coingecko:
        return ['coingecko', 'fred']  # フォールバック
    elif symbol in tier4_alpha:
        return ['alpha_vantage']
    else:
        return ['fred', 'alpha_vantage', 'coingecko']  # デフォルト
```

### 効率実行制御
```python
def execute_by_efficiency(symbols: List[str]) -> Dict:
    """効率重視での実行制御"""
    
    # API別グループ化
    fred_symbols = [s for s in symbols if get_primary_api(s) == 'fred']
    coingecko_symbols = [s for s in symbols if get_primary_api(s) == 'coingecko']  
    alpha_symbols = [s for s in symbols if get_primary_api(s) == 'alpha_vantage']
    
    results = {}
    
    # 1. FRED優先実行（制限なし）
    results.update(execute_fred_batch(fred_symbols))
    
    # 2. CoinGecko実行（制限管理）
    results.update(execute_coingecko_batch(coingecko_symbols))
    
    # 3. Alpha Vantage実行（厳制限）
    results.update(execute_alpha_batch(alpha_symbols))
    
    return results
```

---

## 📊 運用監視メトリクス

### KPI監視項目
```python
monitoring_metrics = {
    "成功率": "target: >85%",
    "実行時間": "target: <30分（全銘柄）", 
    "API使用率": "FRED優先度 target: >60%",
    "エラー率": "target: <5%",
    "レート制限違反": "target: 0件/日"
}
```

### アラート条件
```python
alert_conditions = {
    "CRITICAL": "成功率 < 70%",
    "HIGH": "実行時間 > 45分",
    "MEDIUM": "エラー率 > 10%", 
    "LOW": "レート制限違反 > 0件"
}
```

---

## 🔄 定期見直し計画

### 月次見直し項目
- [ ] API使用統計の分析
- [ ] 成功率・エラー率の評価
- [ ] 新銘柄追加の検討
- [ ] レート制限設定の最適化

### 四半期見直し項目  
- [ ] API料金プランの見直し
- [ ] 代替APIソースの評価
- [ ] データ品質の総合評価
- [ ] システム性能の最適化

---

**最終更新**: 2025-08-08  
**適用版**: v3.0.0  
**次回更新予定**: 2025-09-08