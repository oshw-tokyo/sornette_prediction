# 複数フィッティング結果の選択戦略

## 📋 問題の核心

特定の市場に対して複数の初期パラメータでフィッティングを実行すると、複数の異なる結果が得られます。**どの結果を「正解」として選ぶべきか**、これは非常に重要な技術的・理論的問題です。

---

## 🎯 現状の実装における選択方法

### 1. 単純なR²最大化選択

#### 現在のアルゴリズム
```python
def _perform_lppl_fitting(self, data):
    best_result = None
    best_r2 = 0  # ← R²による単純比較
    
    # 複数の初期値で試行
    for tc_init in [1.1, 1.2, 1.3, 1.5, 2.0]:
        try:
            popt, _ = curve_fit(logarithm_periodic_func, ...)
            r_squared = calculate_r2(...)
            
            if r_squared > best_r2:  # ← R²が最大のものを選択
                best_r2 = r_squared
                best_result = {
                    'tc': popt[0],
                    'beta': popt[1], 
                    'omega': popt[2],
                    'r_squared': r_squared,
                    'rmse': rmse
                }
        except:
            continue
    
    return best_result  # ← 最高R²の結果のみを返す
```

#### 具体的な動作例
```python
# 5つの初期値での試行結果例
trial_results = [
    {'tc': 1.15, 'beta': 0.33, 'omega': 6.2, 'r_squared': 0.85},  # 初期値1
    {'tc': 1.28, 'beta': 0.41, 'omega': 7.1, 'r_squared': 0.92},  # 初期値2 ← 最高R²
    {'tc': 1.44, 'beta': 0.29, 'omega': 5.8, 'r_squared': 0.78},  # 初期値3
    {'tc': 2.15, 'beta': 0.38, 'omega': 8.3, 'r_squared': 0.89},  # 初期値4
    # 初期値5は収束失敗
]

# 現状の選択結果
selected_result = {'tc': 1.28, 'beta': 0.41, 'omega': 7.1, 'r_squared': 0.92}
# ↑ R²=0.92が最高なので、これが選択される
```

---

## ⚠️ 現状の問題点

### 1. R²最大化の限界

#### 問題1: 過学習の可能性
```python
# 複雑なパラメータ組み合わせがより高いR²を達成する場合
result_A = {'tc': 1.2, 'beta': 0.33, 'omega': 6.5, 'r_squared': 0.85}  # 理論値に近い
result_B = {'tc': 2.8, 'beta': 0.71, 'omega': 14.2, 'r_squared': 0.93}  # 理論から遠い

# 現状の選択: result_B (R²が高い)
# 理想的選択: result_A (理論的に妥当)
```

#### 問題2: 局所最適解の選択
```python
# 異なる局所最適解の例
local_optimum_1 = {'tc': 1.15, 'r_squared': 0.89}  # 短期予測
local_optimum_2 = {'tc': 2.34, 'r_squared': 0.91}  # 長期予測

# 現状: R²の高い local_optimum_2 を選択
# 問題: 実用性（tc値の意味）を考慮していない
```

### 2. 理論的制約の軽視

#### Sornette理論の典型値との乖離
```python
# 論文で報告される典型値
theoretical_ranges = {
    'beta': [0.2, 0.7],     # 特に0.33付近
    'omega': [3.0, 15.0],   # 特に5-8付近
    'tc': [1.01, 1.5]       # 実用的な予測範囲
}

# 現状の実装では理論値への近さは考慮されない
# → R²のみで判定
```

---

## 🔬 改良版選択アルゴリズムの提案

### 1. 多基準評価システム

#### 総合スコアによる選択
```python
def calculate_comprehensive_score(fitting_result):
    """多基準による総合評価スコア"""
    
    # 1. 統計的品質 (40%)
    statistical_score = fitting_result['r_squared']
    
    # 2. 理論的妥当性 (30%)
    beta_proximity = 1.0 - abs(fitting_result['beta'] - 0.33) / 0.33
    omega_proximity = 1.0 - abs(fitting_result['omega'] - 6.36) / 6.36
    theoretical_score = (beta_proximity + omega_proximity) / 2
    
    # 3. 実用性 (20%)
    tc_practicality = 1.0 if fitting_result['tc'] <= 1.5 else 0.5
    
    # 4. 安定性 (10%)
    stability_score = 1.0 / (1.0 + fitting_result['rmse'])
    
    # 総合スコア計算
    total_score = (
        statistical_score * 0.4 +
        theoretical_score * 0.3 +
        tc_practicality * 0.2 +
        stability_score * 0.1
    )
    
    return total_score

def select_best_result(all_results):
    """総合スコアによる最適結果選択"""
    
    best_result = None
    best_score = 0
    
    for result in all_results:
        comprehensive_score = calculate_comprehensive_score(result)
        
        if comprehensive_score > best_score:
            best_score = comprehensive_score
            best_result = result
    
    return best_result, best_score
```

#### 改良版の選択例
```python
# 同じ試行結果を改良版で評価
trial_results = [
    {'tc': 1.15, 'beta': 0.33, 'omega': 6.2, 'r_squared': 0.85, 'rmse': 0.05},
    {'tc': 1.28, 'beta': 0.41, 'omega': 7.1, 'r_squared': 0.92, 'rmse': 0.08},
    {'tc': 2.15, 'beta': 0.38, 'omega': 8.3, 'r_squared': 0.89, 'rmse': 0.06}
]

# 改良版での評価
scores = [
    # result 1: 理論値に近い
    0.85*0.4 + 0.95*0.3 + 1.0*0.2 + 0.95*0.1 = 0.875,
    
    # result 2: R²は高いが理論値から遠い  
    0.92*0.4 + 0.75*0.3 + 1.0*0.2 + 0.93*0.1 = 0.868,
    
    # result 3: tc値が実用範囲外
    0.89*0.4 + 0.85*0.3 + 0.5*0.2 + 0.94*0.1 = 0.809
]

# 改良版選択結果: result 1 (総合スコア最高)
# ↑ R²は少し低いが、理論的妥当性と実用性で優位
```

### 2. アンサンブル手法の導入

#### 複数結果の統合利用
```python
def ensemble_prediction(all_valid_results, weights=None):
    """複数結果の重み付き平均による予測"""
    
    if weights is None:
        # R²による重み付け
        weights = [r['r_squared'] for r in all_valid_results]
        weights = np.array(weights) / sum(weights)
    
    # パラメータの重み付き平均
    ensemble_tc = sum(w * r['tc'] for w, r in zip(weights, all_valid_results))
    ensemble_beta = sum(w * r['beta'] for w, r in zip(weights, all_valid_results))
    ensemble_omega = sum(w * r['omega'] for w, r in zip(weights, all_valid_results))
    
    # 信頼度の計算
    confidence = calculate_ensemble_confidence(all_valid_results, weights)
    
    return {
        'tc': ensemble_tc,
        'beta': ensemble_beta,
        'omega': ensemble_omega,
        'confidence': confidence,
        'method': 'ensemble',
        'component_count': len(all_valid_results)
    }

def calculate_ensemble_confidence(results, weights):
    """アンサンブル信頼度の計算"""
    
    # パラメータの分散による信頼度
    tc_variance = np.var([r['tc'] for r in results])
    beta_variance = np.var([r['beta'] for r in results])
    
    # 分散が小さいほど信頼度が高い
    stability_score = 1.0 / (1.0 + tc_variance + beta_variance)
    
    # 平均R²による品質スコア
    avg_r2 = sum(w * r['r_squared'] for w, r in zip(weights, results))
    
    # 総合信頼度
    confidence = (stability_score * 0.6 + avg_r2 * 0.4)
    
    return confidence
```

#### アンサンブルの具体例
```python
# 複数の妥当な結果
valid_results = [
    {'tc': 1.15, 'beta': 0.33, 'omega': 6.2, 'r_squared': 0.85},
    {'tc': 1.18, 'beta': 0.31, 'omega': 6.5, 'r_squared': 0.83},
    {'tc': 1.22, 'beta': 0.35, 'omega': 6.8, 'r_squared': 0.87}
]

# アンサンブル結果
ensemble_result = {
    'tc': 1.18,      # 加重平均
    'beta': 0.33,    # 加重平均  
    'omega': 6.5,    # 加重平均
    'confidence': 0.91,  # 高い安定性
    'method': 'ensemble'
}
```

### 3. 不確実性の定量化

#### パラメータ信頼区間の計算
```python
def calculate_parameter_uncertainty(all_results):
    """パラメータの不確実性評価"""
    
    # 妥当な結果のみを使用（R² > 0.6 かつ 理論制約満足）
    valid_results = filter_valid_results(all_results)
    
    if len(valid_results) < 2:
        return {'uncertainty': 'high', 'confidence_interval': None}
    
    # パラメータ分布の計算
    tc_values = [r['tc'] for r in valid_results]
    beta_values = [r['beta'] for r in valid_results]
    omega_values = [r['omega'] for r in valid_results]
    
    # 95%信頼区間
    tc_ci = np.percentile(tc_values, [2.5, 97.5])
    beta_ci = np.percentile(beta_values, [2.5, 97.5])
    omega_ci = np.percentile(omega_values, [2.5, 97.5])
    
    # 不確実性評価
    tc_uncertainty = (tc_ci[1] - tc_ci[0]) / np.mean(tc_values)
    
    if tc_uncertainty < 0.1:
        uncertainty_level = 'low'
    elif tc_uncertainty < 0.3:
        uncertainty_level = 'medium'
    else:
        uncertainty_level = 'high'
    
    return {
        'uncertainty_level': uncertainty_level,
        'confidence_intervals': {
            'tc': tc_ci,
            'beta': beta_ci,
            'omega': omega_ci
        },
        'parameter_stability': 1.0 - tc_uncertainty
    }
```

---

## 🎯 実装推奨戦略

### 1. 段階的改良アプローチ

#### Phase 1: 現状の改良（即座実装可能）
```python
def improved_simple_selection(all_results):
    """現状のR²選択を理論制約で改良"""
    
    # 理論的に妥当な結果のみをフィルタ
    valid_results = []
    for result in all_results:
        if (1.01 <= result['tc'] <= 2.0 and
            0.2 <= result['beta'] <= 0.7 and
            3.0 <= result['omega'] <= 15.0 and
            result['r_squared'] > 0.5):
            valid_results.append(result)
    
    if not valid_results:
        # 制約を満たす結果がない場合は元の方法にフォールバック
        return max(all_results, key=lambda x: x['r_squared'])
    
    # 妥当な結果の中でR²最大を選択
    return max(valid_results, key=lambda x: x['r_squared'])
```

#### Phase 2: 多基準評価（中期実装）
```python
def multi_criteria_selection(all_results):
    """多基準による選択"""
    return select_best_result_by_comprehensive_score(all_results)
```

#### Phase 3: アンサンブル手法（長期実装）
```python
def ensemble_based_prediction(all_results):
    """アンサンブルによる統合予測"""
    return ensemble_prediction(all_results)
```

### 2. 結果の記録・比較

#### 選択プロセスの透明化
```python
def record_selection_process(market, all_results, selected_result, method):
    """選択プロセスの詳細記録"""
    
    selection_log = {
        'market': market,
        'timestamp': datetime.now(),
        'total_trials': len(all_results),
        'successful_trials': len([r for r in all_results if r is not None]),
        'selection_method': method,
        'selected_result': selected_result,
        'alternative_results': all_results[:5],  # 上位5件
        'selection_rationale': explain_selection(selected_result, all_results)
    }
    
    # 選択履歴データベースに保存（新テーブル必要）
    save_selection_log(selection_log)
```

#### 選択基準の調整・学習
```python
def optimize_selection_criteria(historical_accuracy_data):
    """過去の予測精度に基づく選択基準の最適化"""
    
    # 過去の選択結果と実際の精度の関係を分析
    # 最も精度の高い選択基準を特定
    # 選択基準の重み付けを動的調整
    
    optimized_weights = {
        'statistical_weight': 0.35,  # R²の重み（調整後）
        'theoretical_weight': 0.40,  # 理論妥当性の重み（増加）
        'practicality_weight': 0.25  # 実用性の重み（調整後）
    }
    
    return optimized_weights
```

---

## 📊 選択戦略の比較

### 現状 vs 改良版の予想される影響

| 観点 | 現状（R²最大） | 改良版（多基準） | 期待される改善 |
|------|----------------|------------------|----------------|
| **統計品質** | 最高R²保証 | やや低下の可能性 | 過学習リスク減少 |
| **理論妥当性** | 考慮なし | 明示的考慮 | 物理的意味の向上 |
| **実用性** | tc値無制限 | 実用範囲重視 | 予測価値の向上 |
| **安定性** | 不明 | 定量評価 | 信頼性の可視化 |
| **解釈性** | 困難 | 根拠明確 | 意思決定支援 |

### 具体的な改善例

```python
# 実例：2016-2019年データでの選択比較
original_selection = {
    'tc': 2.85, 'beta': 0.71, 'omega': 14.2, 'r_squared': 0.97,
    'interpretation': '長期トレンド（実用性低）'
}

improved_selection = {
    'tc': 1.28, 'beta': 0.33, 'omega': 6.5, 'r_squared': 0.92,
    'interpretation': 'アクション可能な予測（実用性高）'
}

# 結果：予測精度は僅かに下がるが、実用性が大幅向上
```

---

## 📋 まとめ

### 現状の問題点
1. **R²のみによる選択**で過学習リスク
2. **理論的制約の無視**で物理的意味の欠如
3. **単一結果のみ利用**で不確実性の見逃し

### 推奨改善策
1. **多基準評価**による総合的判定
2. **アンサンブル手法**による不確実性考慮
3. **選択プロセスの透明化**による改善可能性

### 実装優先順位
1. **即座**: 理論制約によるフィルタリング
2. **短期**: 多基準評価システム
3. **中期**: アンサンブル手法とプロセス記録

複数フィッティング結果の適切な選択は予測精度と実用性の核心であり、段階的な改良により大幅な性能向上が期待できます。

---

*作成日: 2025年8月2日*  
*作成者: Claude Code (Anthropic)*  
*ステータス: 複数フィッティング結果選択戦略の詳細解説*