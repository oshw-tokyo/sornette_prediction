# Boulder lppls / FCO 分析サマリー

## 1. FCOとBoulderの関係

### **FCO (Financial Crisis Observatory)**
- **主体**: ETH Zurich（スイス連邦工科大学チューリッヒ校）
- **性質**: 学術研究プロジェクト・理論と方法論の開発元
- **内容**: DS-LPPLS指標の定義と計算方法を確立
- **提供**: 月次レポート（無料）、研究論文、方法論

### **Boulder Investment Technologies**
- **主体**: 民間企業（投資技術会社）
- **性質**: FCO理論の実装ライブラリ（オープンソース）
- **内容**: FCOの方法論をPythonで実装
- **特徴**: MIT License、実用的な実装、417+ stars

**関係**: BoulderはFCOの理論を実装したライブラリ。FCOが「設計図」、Boulderが「実装」の関係。

## 2. LPPLS数式の比較

### 現在の実装（論文準拠）
```python
I(t) = A + B(tc - t)^β + C(tc - t)^β cos(ω ln(tc - t) - φ)
```
- 7パラメータ: A, B, C, tc, β, ω, φ
- 位相φを独立パラメータとして扱う

### Boulder/FCO実装
```python
E[ln(P(t))] = A + B(tc - t)^m + (tc - t)^m [C1 cos(ω ln(tc - t)) + C2 sin(ω ln(tc - t))]
```
- 7パラメータ: A, B, C1, C2, tc, m, ω
- sin/cos成分を分離（C1, C2）

### **結論: 数式は本質的に同一**
三角関数の恒等式により、両者は数学的に等価：
- `C cos(ωt - φ) = C1 cos(ωt) + C2 sin(ωt)`
- ここで `C1 = C cos(φ)`, `C2 = C sin(φ)`

**影響**: 数式レベルでの変更は不要。パラメータ表現の違いのみ。

## 3. Boulder lppls統合の評価

### 利点
✅ **多重時間窓分析実装済み**
- `compute_nested_fits()`メソッド
- `mp_compute_nested_fits()`（並列処理版）
- FCOの126窓分析がすぐ使える

✅ **DS-LPPLS指標計算済み**
- pos_conf（正のバブル）
- neg_conf（負のバブル）
- フィルタリング条件実装済み

✅ **最適化手法の多様性**
- CMA-ES（進化戦略）
- Quantile Regression
- 標準的な最小二乗法

✅ **実績と信頼性**
- MIT License（商用利用可）
- 417+ stars、活発なメンテナンス
- テストスイート完備

### 欠点
⚠️ **カスタマイズ性の制限**
- 内部実装が複雑
- 日本市場向けチューニングが必要な場合に制約

⚠️ **依存関係**
- numba, pandas, xarray等の追加依存
- 既存環境との互換性確認が必要

## 4. 統合戦略の推奨

### **推奨: ハイブリッドアプローチ**

```python
class FCOAnalysisEngine:
    def __init__(self):
        # 現在の実装（論文再現保護）
        self.classic_fitter = LogarithmPeriodicFitter()
        
        # Boulder実装（FCO機能）
        from lppls import LPPLS
        self.boulder_engine = LPPLS
        
    def analyze_fco_style(self, prices):
        """FCO方式の多重時間窓分析"""
        lppls_model = self.boulder_engine(observations=prices)
        
        # 126窓での分析（FCO準拠）
        res = lppls_model.mp_compute_nested_fits(
            window_size=range(125, 751, 5),
            smallest_window_size=125,
            increment=5,
            max_workers=8
        )
        
        # DS-LPPLS Confidence計算
        indicators = lppls_model.compute_indicators(res)
        return indicators
        
    def validate_1987_crash(self):
        """論文再現テスト（現在の実装を使用）"""
        return self.classic_fitter.fit(...)  # 100/100スコア維持
```

### 統合の容易性評価: **容易**

理由：
1. **数式が同一**: パラメータ変換のみで対応可能
2. **独立した実装**: 現在のコードを変更せずに追加可能
3. **段階的移行可能**: 機能ごとに切り替え可能

## 5. 実装計画

### Phase 1: Boulder統合（1週間）
1. Boulderライブラリインストール
2. ラッパークラス作成
3. 基本動作確認

### Phase 2: FCO機能実装（2週間）
1. 126窓分析実装
2. DS-LPPLS Confidence/Trust指標
3. k-meansクラスタリング

### Phase 3: 統合とテスト（1週間）
1. 既存システムとの統合
2. 1987年クラッシュテスト（100/100維持）
3. パフォーマンス最適化

## 6. 結論

- **FCO = 理論・方法論**（ETH Zurich）
- **Boulder = 実装ライブラリ**（FCO準拠）
- **数式は同一**（変更不要）
- **統合は容易**（並行運用可能）
- **推奨: Boulder活用**（開発期間短縮）