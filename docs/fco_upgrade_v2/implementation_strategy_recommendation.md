# Boulder Investment Technologies lppls ライブラリ活用戦略の推奨事項

## エグゼクティブサマリー

Boulder Investment Technologies のlpplsライブラリ（MIT License、417+ stars）は、金融業界で実績のある実装です。現在の実装を**段階的に補完・改良**する戦略を推奨します。完全置き換えではなく、**ハイブリッドアプローチ**が最適です。

---

## 1. Boulder lppls ライブラリの評価

### 1.1 強み

✅ **実績と信頼性**：
- MIT License（商用利用可能）
- 417+ stars、活発なメンテナンス
- 金融業界での実用実績
- 学術論文ベース（Sornette論文引用）

✅ **高度な機能**：
- **CMA-ES（進化戦略）**: 非線形パラメータ最適化の最先端手法
- **Quantile Regression**: L1ノルムベースのロバスト推定
- **並列処理**: マルチスレッド対応のconfidence計算
- **Nested Fits**: FCO準拠の多重時間窓分析

✅ **品質保証**：
- 包括的なテストスイート
- ドキュメント完備
- Jupyter Notebookサンプル

### 1.2 制約事項

⚠️ **パフォーマンス**：
- CMA-ESは単一フィットには優秀だが、confidence指標計算には時間がかかる
- リアルタイム分析には最適化が必要

⚠️ **カスタマイズ性**：
- 内部実装が隠蔽されており、細かい調整が困難
- 日本市場向けパラメータチューニングが必要

---

## 2. 推奨実装戦略：ハイブリッドアプローチ

### 2.1 基本方針

```
現在の実装（論文再現保護） + Boulder lppls（先進機能） = 最強の組み合わせ
```

### 2.2 段階的統合計画

#### **Phase 1: 並行実装（2週間）**
```python
# 現在の実装を保持しつつ、新モジュールを追加
core/
├── fitting/
│   ├── fitter.py                    # 現在の実装（保護対象）
│   ├── advanced_fitter.py            # NEW: Boulder lppls wrapper
│   └── hybrid_analyzer.py            # NEW: 統合分析器
```

#### **Phase 2: 機能補完（3週間）**
```python
class HybridLPPLSAnalyzer:
    """現在の実装とBoulder lpplsの長所を統合"""
    
    def __init__(self):
        self.classic_fitter = LogarithmPeriodicFitter()  # 現在の実装
        self.advanced_fitter = LPPLS()  # Boulder実装
        
    def analyze(self, prices, method='hybrid'):
        if method == 'classic':
            # 論文再現用（100/100スコア保護）
            return self.classic_fitter.fit(prices)
        elif method == 'advanced':
            # CMA-ES/Quantile Regression
            return self.advanced_fitter.fit(prices)
        elif method == 'hybrid':
            # 両方の結果を統合
            return self._combine_results(prices)
```

#### **Phase 3: DS-LPPLS実装（4週間）**
```python
# Boulder lpplsのcompute_nested_fitsを活用
from lppls import LPPLS

def calculate_ds_lppls_confidence(prices):
    """FCO準拠のDS-LPPLS Confidence計算"""
    lppls_model = LPPLS(observations=prices)
    
    # 126時間窓での分析
    res = lppls_model.mp_compute_nested_fits(
        window_size=range(125, 751, 5),  # 126 windows
        smallest_window_size=125,
        increment=5,
        max_workers=8  # 並列処理
    )
    
    # フィルタリング条件適用
    filtered = res[
        (res['damping'] >= 1.0) &
        (res['m'] > 0.1) & (res['m'] < 0.9) &
        (res['omega'] > 2) & (res['omega'] < 25) &
        (res['tc'] > res['t2'])
    ]
    
    confidence = len(filtered) / 126
    return confidence, res
```

---

## 3. 実装上の具体的推奨事項

### 3.1 依存関係管理

```toml
# pyproject.toml または requirements.txt
[dependencies]
lppls = "^0.6.0"  # Boulder実装
numpy = "^1.24.0"
scipy = "^1.10.0"  # 現在の実装用
pandas = "^2.0.0"
```

### 3.2 アーキテクチャ設計

```python
# infrastructure/fitting_engines/
fitting_engines/
├── __init__.py
├── base_engine.py           # 抽象基底クラス
├── classic_engine.py        # 現在の実装（scipy.optimize.curve_fit）
├── boulder_engine.py        # Boulder lppls wrapper
├── hybrid_engine.py         # 統合エンジン
└── benchmark.py            # パフォーマンス比較ツール
```

### 3.3 設定管理

```yaml
# config/fitting_config.yaml
fitting:
  default_engine: "hybrid"
  
  classic:
    n_tries: 10
    bounds: [1.01, 1.5, 0.3, 0.7, ...]
    
  boulder:
    observations: 250
    max_searches: 25
    minimizer: "SLSQP"  # or "CMA-ES" for accuracy
    
  ds_lppls:
    max_window: 750
    min_window: 125
    step_size: 5
    damping_threshold: 1.0
```

---

## 4. リスク管理と移行戦略

### 4.1 リスク軽減策

✅ **論文再現保護**：
```python
# tests/test_reproducibility.py
def test_black_monday_1987():
    """変更後も100/100スコア維持を保証"""
    result = classic_engine.fit(black_monday_data)
    assert result.score == 100
```

✅ **A/Bテスト**：
```python
def compare_engines(prices):
    """新旧実装の結果比較"""
    classic_result = classic_engine.fit(prices)
    boulder_result = boulder_engine.fit(prices)
    
    return {
        'r2_diff': abs(classic_result.r2 - boulder_result.r2),
        'tc_diff': abs(classic_result.tc - boulder_result.tc),
        'performance': boulder_result.time / classic_result.time
    }
```

### 4.2 段階的移行

```mermaid
graph LR
    A[現在の実装] --> B[並行運用]
    B --> C[信頼性検証]
    C --> D[段階的切替]
    D --> E[完全統合]
```

1. **並行運用期（1ヶ月）**: 両実装を並行稼働
2. **検証期（2週間）**: 結果の一致性確認
3. **移行期（2週間）**: ユーザー選択可能
4. **統合期（1週間）**: デフォルト切替

---

## 5. 日本市場向け最適化

### 5.1 パラメータチューニング

```python
# japan_market_config.py
JAPAN_MARKET_PARAMS = {
    'boulder': {
        'observations': 200,  # 日本市場のボラティリティに対応
        'max_searches': 30,   # より詳細な探索
        'minimizer': 'L-BFGS-B'  # 高速化
    },
    'windows': {
        'max': 500,  # 2年（日本市場向け）
        'min': 100,  # 0.4年
        'step': 3    # より細かいステップ
    }
}
```

### 5.2 カスタム拡張

```python
class JapanMarketLPPLS(LPPLS):
    """日本市場向けカスタマイズ"""
    
    def __init__(self, observations):
        super().__init__(observations)
        self.configure_for_japan_market()
        
    def configure_for_japan_market(self):
        # 日経平均特有のパターンに対応
        self.set_param_bounds({
            'tc': (1.01, 1.3),  # より短期の予測
            'm': (0.2, 0.6),    # 日本市場のバブル特性
            'omega': (4, 10)    # 振動頻度の調整
        })
```

---

## 6. 推奨アクションプラン

### 即座に実行（1週間以内）

1. **Boulder lppls インストールとテスト**：
```bash
pip install lppls
python -c "from lppls import LPPLS; print('Success')"
```

2. **ベンチマーク作成**：
```python
# workspace_for_claude/benchmark_boulder_lppls.py
import time
from lppls import LPPLS
from core.fitting.fitter import LogarithmPeriodicFitter

def benchmark_comparison(prices):
    # 現在の実装
    start = time.time()
    classic_result = LogarithmPeriodicFitter().fit(prices)
    classic_time = time.time() - start
    
    # Boulder実装
    start = time.time()
    lppls = LPPLS(observations=prices)
    boulder_result = lppls.fit()
    boulder_time = time.time() - start
    
    print(f"Classic: {classic_time:.2f}s, R²={classic_result.r_squared:.3f}")
    print(f"Boulder: {boulder_time:.2f}s, R²={boulder_result['res']['r2']:.3f}")
```

### 短期目標（2-4週間）

3. **ハイブリッドエンジン実装**
4. **DS-LPPLS Confidence実装**
5. **論文再現テストの継続的実行**

### 中期目標（1-2ヶ月）

6. **完全な統合テストスイート**
7. **パフォーマンス最適化**
8. **ドキュメント更新**

---

## 7. 結論

### ✅ **推奨アプローチ：補完的統合**

現在の実装を**保護・維持**しながら、Boulder lpplsの**先進機能を選択的に統合**する戦略が最適です。

**理由**：
1. **論文再現性の保護**: 現在の100/100スコアを維持
2. **先進機能の活用**: CMA-ES、Quantile Regression等
3. **リスク最小化**: 段階的移行で問題を早期発見
4. **柔軟性確保**: 用途に応じて最適な手法を選択

### ❌ **避けるべきアプローチ**

- **完全置き換え**: 論文再現性を失うリスク
- **独立並行開発**: メンテナンスコスト増大
- **無計画な統合**: 品質低下のリスク

### 📊 **意思決定マトリクス**

| アプローチ | 論文再現性 | 先進機能 | リスク | 推奨度 |
|-----------|-----------|---------|--------|--------|
| 現状維持 | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | 30% |
| 完全置換 | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 10% |
| **補完的統合** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | **90%** |

---

## 8. 次のステップ

1. **本推奨事項のレビューと承認**
2. **feature/boulder-integration ブランチ作成**
3. **最小限のPoCを1週間で実装**
4. **結果を評価して本格実装へ**

Boulder lpplsライブラリは強力なツールですが、現在の実装の価値も高いです。両者の長所を活かすハイブリッドアプローチにより、**学術的厳密性**と**産業レベルの実用性**を両立できます。

---

*作成日: 2025年1月*
*作成者: Claude Code*