# 論文再現テスト戦略

## 重要な確認事項への回答

### **質問**: 完全置き換え後、論文再現テストはFCOで実施するのか、現在のLPPLモデルを維持するのか？

### **回答**: **最終的にはFCOで実施**

理由：
1. **数式が本質的に同一**であることを確認済み
2. FCO（Boulder実装）でも同じ結果が得られるはず
3. 統一された実装による保守性向上

## 実装戦略

### Phase 1: 並行検証期間（移行期）
```python
class TransitionValidator:
    """移行期の検証クラス"""
    
    def validate_1987_crash(self):
        # 1. 現在の実装で検証
        classic_result = self.classic_fitter.validate_1987()
        assert classic_result.score == 100  # 必須
        
        # 2. FCO実装で検証
        fco_result = self.fco_engine.validate_1987()
        
        # 3. 結果を比較
        self.compare_results(classic_result, fco_result)
        
        # 両方が100/100になることを確認
        return {
            'classic': classic_result,
            'fco': fco_result,
            'match': self.results_match(classic_result, fco_result)
        }
```

### Phase 2: FCO実装の調整
```python
class FCOCalibration:
    """FCO実装を論文再現に調整"""
    
    def calibrate_for_1987(self):
        # 単一窓（706日）でのフィッティング
        # FCOの126窓ではなく、論文準拠の特定窓を使用
        
        result = self.fco_engine.fit_single_window(
            window_size=706,  # 1987年データ点数
            tc_constraint=(1.01, 1.5),
            beta_constraint=(0.30, 0.45),
            omega_constraint=(5.0, 8.0)
        )
        
        # 論文報告値との比較
        assert abs(result.beta - 0.33) < 0.03  # 論文: β = 0.33 ± 0.03
        assert 6 <= result.omega <= 8  # 論文: ω = 6-8
        
        return result
```

### Phase 3: 完全移行後
```python
class FCOValidator:
    """完全移行後の検証（FCOのみ）"""
    
    def validate_1987_crash(self):
        # FCO実装で単一窓分析モードを使用
        result = self.fco_engine.validate_paper_reproduction(
            test_case='1987',
            mode='single_window',  # 論文再現用
            expected_score=100
        )
        
        # DS-LPPLS指標も参考値として計算
        confidence = self.fco_engine.compute_confidence(
            mode='multi_window'  # 126窓分析
        )
        
        return {
            'reproduction_score': result.score,  # 100/100必須
            'ds_lppls_confidence': confidence,  # 参考値
            'status': 'PASSED' if result.score == 100 else 'FAILED'
        }
```

## 実装における重要ポイント

### 1. **単一窓モードの維持**
FCO実装でも、論文再現テスト用に単一窓分析機能を保持：
- 706日間のデータ
- 特定のパラメータ制約
- 論文と同じ評価基準

### 2. **パラメータマッピング**
現在の実装とFCOのパラメータ対応：
| 現在 | FCO/Boulder | 変換 |
|------|-------------|------|
| β | m | 同一 |
| φ | - | C1=C*cos(φ), C2=C*sin(φ) |
| C | C1, C2 | 三角関数変換 |

### 3. **検証基準の統一**
```python
PAPER_REPRODUCTION_CRITERIA = {
    '1987': {
        'data_points': 706,
        'expected_beta': 0.33,
        'beta_tolerance': 0.03,
        'expected_omega': 7.0,
        'omega_range': (6.0, 8.0),
        'min_r_squared': 0.95,
        'required_score': 100
    }
}
```

## 移行スケジュール

### Week 1-2: 並行実装
- ✅ 現在の実装で100/100維持
- 🔄 FCO実装で同等の結果を目指す

### Week 3: 検証と調整
- 🔄 両実装の結果比較
- 🔄 FCOパラメータ調整

### Week 4: 完全移行
- ✅ FCOで100/100達成
- ✅ 現在の実装を廃止可能に

## リスク管理

### リスク1: FCOで100/100が出ない
**対策**: 
- 単一窓モードの特別実装
- パラメータ制約の調整
- 最悪の場合、論文再現テストのみ旧実装を残す

### リスク2: 数値精度の違い
**対策**:
- 許容誤差の適切な設定
- 数値計算ライブラリの統一

## 結論

**最終的にFCOで論文再現テストを実施する方針**で進めます。ただし：

1. 移行期は両方で検証
2. FCOに単一窓モードを実装
3. 100/100スコアの維持を最優先
4. 完全移行後は旧実装を削除

この方針により、科学的正確性を保ちつつ、統一された実装に移行できます。