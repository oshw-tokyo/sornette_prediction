# API割り当て戦略ガイド

## 🎯 目的

新しいAPIプロバイダー追加時の**銘柄割り当て戦略**を定義し、システムの一貫性と効率性を保証する。

---

## 📊 現在のAPI構成（2025-08-09時点）

| プロバイダー | 担当銘柄数 | 信頼性 | レート制限 | コスト | 専門分野 |
|-------------|------------|---------|------------|---------|----------|
| **FRED** | 24銘柄 | ⭐⭐⭐⭐⭐ | 無制限 | 完全無料 | 政府統計、インデックス、マクロ指標 |
| **CoinGecko** | 35銘柄 | ⭐⭐⭐⭐ | 20 calls/min | 無料版利用 | 仮想通貨専門 |
| **Alpha Vantage** | 20銘柄 | ⭐⭐⭐ | 5 calls/min | 500 req/日 | 個別株、ETF、債券 |

**総計**: 79銘柄

---

## 🚀 新API追加時の割り当て基準

### A. **信頼性評価（40点満点）**

| 項目 | 評価基準 | 配点 |
|------|----------|------|
| **データ精度** | 公的機関=10, 大手金融=8, 専門API=6, 一般=4 | 10点 |
| **更新頻度** | リアルタイム=10, 日次=8, 週次=6, 月次=4 | 10点 |
| **履歴データ** | 10年以上=10, 5-10年=8, 2-5年=6, 2年未満=4 | 10点 |
| **サービス安定性** | 99.9%以上=10, 99%以上=8, 95%以上=6, それ以下=4 | 10点 |

### B. **アクセス性評価（30点満点）**

| 項目 | 評価基準 | 配点 |
|------|----------|------|
| **レート制限** | 無制限=15, 100+/min=12, 50-99/min=9, 10-49/min=6, 10未満=3 | 15点 |
| **無料枠** | 完全無料=15, 大容量無料=12, 中容量無料=9, 小容量無料=6, 有料のみ=3 | 15点 |

### C. **専門性評価（20点満点）**

| 項目 | 評価基準 | 配点 |
|------|----------|------|
| **カバレッジ** | 完全専門=20, 高専門=15, 中専門=10, 低専門=5 | 20点 |

### D. **統合容易性評価（10点満点）**

| 項目 | 評価基準 | 配点 |
|------|----------|------|
| **API設計** | RESTful+JSON=10, RESTful=8, SOAP=6, その他=4 | 5点 |
| **ドキュメント** | 充実=5, 標準=4, 不足=2, 無し=1 | 5点 |

---

## 🎯 割り当て決定アルゴリズム

### **ステップ1: 総合スコア計算**
```
総合スコア = 信頼性(40) + アクセス性(30) + 専門性(20) + 統合性(10)
最大100点
```

### **ステップ2: 専門分野マッチング**
1. **仮想通貨**: CoinGecko専門（例外: FRED対応の場合はFRED優先）
2. **政府統計・インデックス**: FRED最優先
3. **個別株・ETF**: 最高スコアAPI優先
4. **債券・商品**: 専門APIがあれば優先、なければ最高スコアAPI

### **ステップ3: 負荷分散考慮**
- 単一APIへの過度な集中を避ける
- レート制限の厳しいAPIは銘柄数を制限
- 無料APIの持続可能性を考慮

---

## 📋 現在のAPI評価（参考）

### **FRED (Federal Reserve Economic Data)**
- **総合スコア**: 95/100
- **信頼性**: 40/40（政府機関、完璧な精度・更新・履歴・安定性）
- **アクセス性**: 30/30（無制限、完全無料）
- **専門性**: 20/20（マクロ経済・金融統計の完全専門）
- **統合性**: 5/10（古いAPI設計だが安定）

### **CoinGecko (Cryptocurrency Data)**
- **総合スコア**: 76/100
- **信頼性**: 32/40（専門API、高精度、日次更新、中程度の履歴）
- **アクセス性**: 24/30（20calls/min、無料版制限あり）
- **専門性**: 20/20（仮想通貨の完全専門）
- **統合性**: 0/10（RESTful、充実ドキュメント）

### **Alpha Vantage (Stock & Financial Data)**
- **総合スコア**: 64/100
- **信頼性**: 28/40（大手金融API、高精度、日次更新）
- **アクセス性**: 18/30（5calls/min、500req/日制限）
- **専門性**: 10/20（個別株・ETF中専門）
- **統合性**: 8/10（RESTful、標準的ドキュメント）

---

## 🔧 実装ガイドライン

### **新API追加時の手順**

1. **評価実施**
   ```bash
   # 評価スコア算出
   python tools/api_evaluator.py --provider NEW_API_NAME
   ```

2. **専門分野確認**
   ```bash
   # カバレッジ分析
   python tools/coverage_analyzer.py --provider NEW_API_NAME
   ```

3. **割り当て提案生成**
   ```bash
   # 自動割り当て提案
   python tools/assignment_optimizer.py --add NEW_API_NAME
   ```

4. **カタログ更新**
   ```json
   // market_data_catalog.json
   "SYMBOL": {
     "data_sources": {
       "primary": {
         "provider": "new_api_name",
         "symbol": "MAPPED_SYMBOL",
         "assignment_reason": "Score: 85/100, Specialization: crypto",
         "assignment_date": "2025-08-09"
       }
     }
   }
   ```

### **割り当て変更時の影響評価**

```bash
# 変更前テスト
python entry_points/main.py validate --crash 1987

# 割り当て変更実行
python tools/reassign_symbols.py --from OLD_API --to NEW_API --symbols "SYM1,SYM2"

# 変更後テスト（100/100スコア維持必須）
python entry_points/main.py validate --crash 1987
```

---

## 🎯 AI支援による最適化

### **自動評価システム（実装予定）**

```python
class APIEvaluator:
    """新API自動評価システム"""
    
    def evaluate_api(self, provider_name: str, api_config: dict) -> dict:
        """
        Args:
            provider_name: API名
            api_config: API設定情報
            
        Returns:
            dict: 評価結果（スコア、推奨割り当て、理由）
        """
        scores = {
            'reliability': self._evaluate_reliability(api_config),
            'accessibility': self._evaluate_accessibility(api_config),
            'specialization': self._evaluate_specialization(api_config),
            'integration': self._evaluate_integration(api_config)
        }
        
        total_score = sum(scores.values())
        recommendations = self._generate_recommendations(scores, api_config)
        
        return {
            'total_score': total_score,
            'detailed_scores': scores,
            'recommendations': recommendations,
            'risk_assessment': self._assess_risks(api_config)
        }
```

### **負荷分散最適化**

```python
class LoadBalancer:
    """API負荷分散最適化"""
    
    def optimize_assignment(self, apis: list, symbols: list) -> dict:
        """
        レート制限・コスト・信頼性を考慮した最適割り当て
        
        Returns:
            dict: 最適化された割り当て提案
        """
        pass
```

---

## ⚠️ 重要な制約

### **1. 論文再現性保護**
- **NASDAQCOM**: FRED固定（1987年検証100/100スコア維持必須）
- 歴史的検証に使用される銘柄の変更は禁止

### **2. 排他的設計維持**
- 1銘柄 = 1API の原則を厳守
- fallback機能は実装しない

### **3. コスト管理**
- 無料APIの利用制限を超えない
- 有料APIの導入は費用対効果を厳密に評価

---

## 📊 モニタリング指標

### **API健全性監視**
- **成功率**: >95% 維持必須
- **レスポンス時間**: 平均<2秒
- **レート制限遵守**: 違反0件/日

### **データ品質監視**
- **データ欠損**: <1%
- **価格異常**: 前日比±50%超の検出・アラート
- **更新遅延**: 1日以内の更新

---

## 🔄 定期レビュー

### **四半期レビュー（年4回）**
1. API提供者の信頼性評価更新
2. レート制限・価格変更の影響評価
3. 新API候補の調査・評価

### **年次レビュー**
1. 全割り当ての最適化
2. コスト効率性の総合評価
3. 技術的負債の解消

---

**策定日**: 2025-08-09  
**最終更新**: 2025-08-09  
**責任者**: システムアーキテクト  
**承認者**: プロジェクト管理者