# FCO方式 vs 現在の実装：複数ウィンドウフィッティングの詳細比較

## エグゼクティブサマリー

現在の実装は、FCO方式と**異なるアプローチ**を採用しています。FCOは「一つの分析で126窓を同時計算」、現在は「週次で単一窓分析を蓄積」です。結果的に似たデータが得られますが、**統計的な意味と信頼性が大きく異なります**。

---

## 1. FCO方式：統合型マルチウィンドウ分析

### 1.1 基本構造

```
【1回の分析で】
- 126個の異なる時間窓（125-750日）
- 同一時点（現在）を終点として
- すべて同時に計算
- 統計的に統合して1つの予測を出力
```

### 1.2 出力形式

```python
# FCOの1回の分析結果
{
    "analysis_date": "2025-09-02",
    "symbol": "NIKKEI225",
    "ds_lppls_confidence": 0.76,  # 126窓の統合指標
    "predicted_crash_date": "2025-12-15",  # 統計的中央値
    "confidence_interval": ["2025-11-20", "2026-01-10"],
    "window_results": [
        {"window": 750, "tc": "2025-11-01", "valid": true},
        {"window": 745, "tc": "2025-11-05", "valid": true},
        # ... 124個の中間結果
        {"window": 125, "tc": "2025-12-20", "valid": false}
    ]
}
```

### 1.3 統計的処理

```python
def fco_analysis(prices, current_date):
    """FCO方式：1回で完結する統合分析"""
    all_results = []
    
    # 126窓すべてを一度に計算
    for window_size in range(750, 124, -5):
        result = lppl_fit(prices[-window_size:])
        all_results.append(result)
    
    # 統計的統合（フィルタリング→中央値）
    valid_results = filter_by_conditions(all_results)
    confidence = len(valid_results) / 126
    
    # 最終的な予測は統計的に決定
    final_tc = median([r.tc for r in valid_results])
    
    return {
        'confidence': confidence,
        'prediction': final_tc,
        'is_reliable': confidence > 0.5  # 閾値判定
    }
```

---

## 2. 現在の実装：時系列蓄積型分析

### 2.1 基本構造

```
【週次で繰り返し】
- 1個の固定時間窓（通常365日）
- 毎週異なる時点を終点として
- 個別に計算・保存
- 後からGUIでクラスタリング
```

### 2.2 出力形式

```python
# 現在の実装：複数週の個別結果
[
    # 週1
    {
        "analysis_basis_date": "2025-08-26",
        "window": 365,
        "tc": "2025-12-01",
        "r_squared": 0.85
    },
    # 週2
    {
        "analysis_basis_date": "2025-09-02",
        "window": 365,
        "tc": "2025-12-10",
        "r_squared": 0.87
    },
    # 週3...
]
```

### 2.3 処理フロー

```python
def current_implementation():
    """現在の実装：週次の個別分析を蓄積"""
    
    # 週次スケジューラが実行
    def weekly_analysis(date):
        prices = get_prices_until(date)
        result = lppl_fit(prices[-365:])  # 固定窓
        save_to_db(result)
    
    # GUIで後から統合表示
    def dashboard_clustering():
        results = load_from_db(last_n_weeks=20)
        clusters = dbscan_clustering(results)
        display_clusters(clusters)
```

---

## 3. 決定的な違い

### 3.1 統計的信頼性

| 観点 | FCO方式 | 現在の実装 |
|------|---------|------------|
| **サンプル数** | 126（1時点） | 20-50（複数週） |
| **独立性** | 高（異なる窓サイズ） | 低（同じ窓、時間差） |
| **ノイズ耐性** | 高（多重検証） | 中（時系列平滑化） |
| **即時性** | 1回で完結 | 数週間の蓄積必要 |

### 3.2 情報の質

**FCO方式の利点**：
```
✅ 短期・中期・長期を同時に捉える
✅ 1回の分析で統計的に有意な結果
✅ DS-LPPLS Confidenceという定量指標
✅ 異常値の即座の検出
```

**現在の実装の利点**：
```
✅ 時系列での予測の推移を追跡
✅ 計算負荷が低い（週1回、単一窓）
✅ トレンドの変化を視覚的に把握
✅ 実装がシンプル
```

---

## 4. 具体例での比較

### シナリオ：2025年9月2日時点でのバブル検出

**FCO方式**：
```
9月2日の分析：
- 750日窓：バブル初期（2023年から）を検出 → tc=2026年3月
- 500日窓：成長期（2024年から）を検出 → tc=2025年12月
- 250日窓：成熟期（2025年から）を検出 → tc=2025年10月
- 結果：Confidence=72%、予測=2025年12月（中央値）
→ 即座に「高信頼度の警告」を発行
```

**現在の実装**：
```
8月5日の分析：365日窓 → tc=2025年11月
8月12日の分析：365日窓 → tc=2025年11月
8月19日の分析：365日窓 → tc=2025年12月
8月26日の分析：365日窓 → tc=2025年12月
9月2日の分析：365日窓 → tc=2026年1月
→ クラスタリング結果：「11-12月に集中」
→ トレンドは把握できるが、統計的信頼度は不明
```

---

## 5. 実質的に同じか？

### 答え：**似て非なるもの**

**表面的な類似点**：
- 複数の分析結果を使用 ✓
- クラスタリングで統合 ✓
- 予測日の分布を可視化 ✓

**本質的な相違点**：

| 要素 | FCO | 現在 | 影響 |
|------|-----|------|------|
| **時間スケール** | 多重（125-750日） | 単一（365日） | FCOは多様なパターンを検出 |
| **同時性** | 同一時点で全計算 | 週次で逐次計算 | FCOは即座に判定可能 |
| **統計的根拠** | 126サンプルの分布 | 時系列の推移 | FCOは信頼区間を算出可能 |
| **パラメータ取捨選択** | フィルタリング条件で自動 | すべて保存・表示 | FCOは質の保証 |

---

## 6. 改善提案：ハイブリッドアプローチ

### 6.1 現在の実装を活かしつつFCO要素を追加

```python
class HybridAnalyzer:
    """現在の週次分析 + FCO的な多重窓分析"""
    
    def weekly_comprehensive_analysis(self, date):
        """週次実行だが、複数窓を同時分析"""
        
        # 1. FCO風の多重窓分析（簡易版）
        windows = [125, 250, 365, 500, 750]  # 5窓に限定
        multi_results = []
        
        for window in windows:
            if len(prices) >= window:
                result = lppl_fit(prices[-window:])
                multi_results.append(result)
        
        # 2. 簡易的なConfidence計算
        valid_count = sum(1 for r in multi_results if r.is_valid())
        confidence = valid_count / len(windows)
        
        # 3. 現在の単一窓分析も実行（互換性維持）
        standard_result = lppl_fit(prices[-365:])
        
        # 4. 両方を保存
        save_comprehensive_result({
            'standard': standard_result,
            'multi_window': multi_results,
            'confidence': confidence
        })
```

### 6.2 段階的移行計画

**Phase 1**：現在の実装を維持しつつ、週次で5窓分析を追加
**Phase 2**：信頼度指標の導入、ダッシュボードに表示
**Phase 3**：完全な126窓分析へ移行（計算リソース確保後）

---

## 7. 結論

**現在の実装は有効だが、FCO方式とは本質的に異なる**：

1. **情報の次元が違う**
   - FCO：空間的（異なる時間スケール）
   - 現在：時間的（同じスケールの時系列）

2. **得られる洞察が違う**
   - FCO：「今この瞬間の多面的な危険度」
   - 現在：「予測の時間的な変化傾向」

3. **最適な使い分け**
   - FCO方式：緊急の意思決定、高信頼度が必要な場面
   - 現在方式：長期モニタリング、トレンド把握

**推奨**：両方式を併用することで、より包括的なリスク管理が可能になります。

---

*作成日: 2025年9月*
*作成者: Claude Code*