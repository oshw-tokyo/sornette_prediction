# FCO実装ギャップ分析と実装要件

## 1. FCO方式の核心要素

### 1.1 DS-LPPLS Confidence Indicator（最重要）
**FCO定義**: 異なるサイズの時間窓で検出された超指数的価格動向の存在を定量化

**計算方法**:
- 126個の時間窓（125-750日、5日刻み）で同時フィッティング
- フィルタリング条件を満たすフィット数 / 総窓数
- 1回の分析で完結する統合指標

### 1.2 フィルタリング条件（Filtering Condition 1）
```python
# FCOの成功判定条件
damping >= 1.0  # クラッシュハザード率h(t)が非負
0.1 < m < 0.9   # べき乗指数の理論的範囲
2 < omega < 25  # 角周波数の妥当な範囲
t2 < tc < t2 + dt  # 予測が未来であること
```

### 1.3 クラスタリング分析
- k-meansクラスタリング（現在のDBSCANではない）
- 最大クラスターの統計量：μtc（平均）、σtc（標準偏差）
- シナリオ確率 = 最大クラスター内フィット数 / 全フィット数

## 2. 現在の実装との決定的な差異

### 2.1 分析アプローチの根本的違い

| 観点 | FCO方式 | 現在の実装 | ギャップ |
|------|---------|------------|----------|
| **分析単位** | 1回で126窓同時 | 日次で1窓ずつ | 統計的意味が異なる |
| **時間窓構成** | 125-750日の多様な窓 | 固定365日窓 | 多重スケール分析なし |
| **統合方法** | Confidence指標で統合 | 後からGUIでクラスタリング | リアルタイム指標なし |
| **クラスタリング** | k-means | DBSCAN | アルゴリズム差異 |
| **予測統合** | 統計的中央値 | 時系列追跡 | 予測精度の違い |

### 2.2 データフローの違い

**FCO**:
```
現在時点 → 126窓同時分析 → Confidence計算 → 即座に信頼性判定
```

**現在**:
```
週1 → 1窓分析 → DB保存 → ... → 週20 → GUIで統合表示
```

## 3. 実装要件

### 3.1 必須実装機能

#### Phase 1: 多重時間窓エンジン（最優先）
```python
class MultiWindowLPPLSEngine:
    def __init__(self):
        self.windows = range(125, 751, 5)  # 126窓
        self.filtering_conditions = {
            'damping': (1.0, float('inf')),
            'm': (0.1, 0.9),
            'omega': (2, 25),
            'tc_future': True
        }
    
    def compute_ds_lppls_confidence(self, prices):
        """FCO準拠のDS-LPPLS Confidence計算"""
        # 126窓で並列フィッティング
        # フィルタリング適用
        # Confidence指標計算
        pass
```

#### Phase 2: Trust指標（ブートストラップ）
```python
def calculate_ds_lppls_trust(prices, num_bootstrap=100):
    """統計的信頼性のメタ指標"""
    # 合成時系列生成
    # 各系列でConfidence計算
    # Trust指標算出
    pass
```

#### Phase 3: 統合レポートシステム
- FCO形式のテーブル出力
- Bubble Data: サイズ、CAGR、Duration、Progress
- Cluster Analysis: μtc、σtc、Scenario Probability

### 3.2 Boulder lppls活用戦略

**推奨アプローチ**: ハイブリッド実装

```python
# Boulder lpplsの機能を活用
from lppls import LPPLS

class HybridFCOEngine:
    def __init__(self):
        self.boulder_engine = LPPLS()  # Boulder実装
        self.classic_engine = LogarithmPeriodicFitter()  # 現在の実装
    
    def analyze_fco_style(self, prices):
        # Boulder のcompute_nested_fitsを活用
        res = self.boulder_engine.mp_compute_nested_fits(
            window_size=range(125, 751, 5),
            smallest_window_size=125,
            increment=5,
            max_workers=8
        )
        
        # FCOフィルタリング条件適用
        confidence = self._apply_fco_filtering(res)
        return confidence
```

## 4. 実装優先順位

### 🔴 Critical（1-2週間）
1. **多重時間窓エンジン実装**
   - 126窓同時分析機能
   - DS-LPPLS Confidence計算
   - FCOフィルタリング条件

### 🟠 High（3-4週間）
2. **Boulder lppls統合**
   - compute_nested_fits活用
   - CMA-ES最適化オプション
   - 並列処理最適化

3. **k-meansクラスタリング実装**
   - 現在のDBSCANと並行運用
   - シナリオ確率計算

### 🟡 Medium（5-6週間）
4. **Trust指標実装**
   - ブートストラップ法
   - 統計的信頼性評価

5. **FCO形式レポート生成**
   - Bubble Dataセクション
   - Cluster Analysisセクション
   - 視覚化の統一

## 5. 移行戦略

### 5.1 段階的移行計画

**Step 1: 並行運用期間（1ヶ月）**
- 現在の日次分析を継続
- FCO方式を別トラックで実装
- 結果を比較・検証

**Step 2: ハイブリッド運用（2ヶ月目）**
- 両方式の結果を統合表示
- ユーザーが選択可能
- フィードバック収集

**Step 3: FCO主導移行（3ヶ月目）**
- FCO方式をデフォルトに
- 日次分析は補助的に維持
- 完全移行の準備

### 5.2 後方互換性の維持

```python
class BackwardCompatibleAnalyzer:
    def analyze(self, symbol, method='hybrid'):
        if method == 'legacy':
            # 現在の日次分析
            return self.weekly_analysis(symbol)
        elif method == 'fco':
            # FCO方式
            return self.fco_analysis(symbol)
        elif method == 'hybrid':
            # 両方の結果を統合
            return self.hybrid_analysis(symbol)
```

## 6. 技術的課題と対策

### 6.1 計算負荷
**課題**: 126窓の同時計算は重い
**対策**: 
- Boulder lpplsの並列処理活用
- Redis/Memcachedでキャッシュ
- GPUアクセラレーション検討

### 6.2 データ要件
**課題**: 750日以上の履歴データが必要
**対策**:
- データ不足時は窓数を自動調整
- 短期窓（125-250日）だけでも計算

### 6.3 リアルタイム性
**課題**: 126窓計算に時間がかかる
**対策**:
- 差分更新アルゴリズム
- 前日結果をベースに更新

## 7. 法的コンプライアンス対応

### 7.1 表示変更要件
- 「クラッシュ予測」→「tc値分布」
- 「危険度」→「DS-LPPLS Confidence」
- 「推奨アクション」→「数理モデル出力」

### 7.2 免責事項
- 全ページに「研究・教育目的」表示
- 確率的表現の徹底
- 投資判断は利用者責任の明記

## 8. 実装チェックリスト

- [ ] 多重時間窓エンジン実装
- [ ] DS-LPPLS Confidence計算
- [ ] FCOフィルタリング条件
- [ ] Boulder lppls統合
- [ ] k-meansクラスタリング
- [ ] Trust指標（ブートストラップ）
- [ ] FCO形式レポート生成
- [ ] 法的コンプライアンス対応
- [ ] パフォーマンス最適化
- [ ] ドキュメント更新

## 9. 次のアクション

1. **feature/fco-upgrade ブランチ作成**
2. **多重時間窓エンジンのプロトタイプ実装**
3. **Boulder lppls動作検証**
4. **1987年テストケースでの検証**