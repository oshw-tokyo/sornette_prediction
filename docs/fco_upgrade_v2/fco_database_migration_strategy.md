# 📊 FCOデータベース移行戦略

## 概要
このドキュメントは、既存のLPPL分析システムからFCO（Financial Crisis Observatory）方式への移行戦略を定義します。

**最終更新**: 2025-09-12  
**ステータス**: 実装開始

## 1. 🎯 移行方針

### 基本原則
- **全窓保存方式**: 126窓すべてのフィッティング結果を保存
- **後方互換性維持**: 既存システムと並行運用
- **段階的最適化**: 実使用パターンに基づく事後最適化

### データ保存戦略
```
Phase 1 (現在): 全データ保存 → Phase 2 (3ヶ月後): 使用分析 → Phase 3 (6ヶ月後): 最適化
```

## 2. 📐 データベース構造

### テーブル関係図
```sql
fco_analysis_results (メインテーブル)
├── id (PRIMARY KEY)
├── symbol
├── ds_lppls_confidence      -- DS-LPPLS正のバブル信頼度
├── ds_lppls_confidence_neg  -- DS-LPPLS負のバブル信頼度
├── predicted_tc              -- 予測臨界時間（中央値）
├── num_windows              -- 分析窓数（通常126）
└── num_qualified_fits       -- 条件適合窓数

fco_window_fits (詳細テーブル)
├── id
├── analysis_id (FOREIGN KEY → fco_analysis_results.id)
├── window_size              -- 窓サイズ（125-750）
├── tc, m, w                 -- LPPLパラメータ
├── r_squared                -- フィッティング品質
├── damping                  -- ダンピング係数
└── is_qualified             -- FCO条件適合フラグ
```

### 既存LPPLとの違い
| 項目 | 既存LPPL | FCO |
|------|---------|-----|
| パラメータセット | 1組 | 126組 |
| 主要指標 | R² | DS-LPPLS信頼度 |
| 予測値 | 単一tc | tc分布（中央値・標準偏差） |
| データ量/分析 | 約2KB | 約15KB |

## 3. 💾 データサイズ見積もり

### 年間データ量予測
```python
# 基本パラメータ
銘柄数 = 80
分析頻度 = 365日/年
窓数/分析 = 126
パラメータ数/窓 = 10

# 計算
1窓のサイズ = 10 × 8バイト = 80バイト
1分析のサイズ = 126 × 80バイト + メタデータ = 約15KB
年間サイズ = 80 × 365 × 15KB = 438MB/年

# 5年運用
5年後のDBサイズ = 約2.2GB
```

### パフォーマンス保証
- SQLiteは100GBまで高速動作
- 適切なインデックスで370万レコードも問題なし
- 現実的な運用で性能問題なし

## 4. 🔄 移行実装計画

### Phase 1: 全窓保存実装（2025年9月）
```python
def save_fco_analysis(result):
    # 1. メインテーブルに集約データ保存
    main_id = save_main_result(result)
    
    # 2. 全126窓の詳細を保存
    for window in result.all_windows:
        save_window_detail(main_id, window)
```

### Phase 2: 使用パターン分析（2025年12月）
```sql
-- アクセスログ収集
CREATE TABLE window_access_log (
    window_id INTEGER,
    access_date TIMESTAMP,
    access_type TEXT
);

-- 分析クエリ
SELECT r_squared, COUNT(*) as access_count
FROM fco_window_fits w
JOIN window_access_log l ON w.id = l.window_id
GROUP BY r_squared;
```

### Phase 3: データ最適化（2026年3月）
```python
def optimize_storage():
    # 低品質・古いデータの削除
    delete_poor_quality_windows(
        age_days=90,
        r_squared_threshold=0.6,
        keep_representative=True
    )
```

## 5. 🎨 ダッシュボード対応

### 表示戦略
1. **代表窓方式**（初期実装）
   - 最高R²の窓のLPPL曲線を表示
   - 既存コードの変更最小限

2. **信頼区間方式**（将来拡張）
   - 複数窓から信頼区間を計算
   - 予測の不確実性を可視化

### 互換性維持
```python
class UnifiedResultsDatabase:
    def get_display_parameters(self, analysis_id):
        if self.is_fco_analysis(analysis_id):
            # FCOから代表窓を選択
            return self.get_best_window(analysis_id)
        else:
            # 既存LPPLデータをそのまま返す
            return self.get_lppl_parameters(analysis_id)
```

## 6. 🔧 データ管理ユーティリティ

### データ抽出ツール
```python
class FCODataExtractor:
    def get_high_confidence_analyses(self, threshold=0.5):
        """高信頼度の分析を抽出"""
        
    def get_tc_convergence(self, symbol, days=30):
        """tc値の収束分析"""
        
    def export_representative_windows(self):
        """代表窓のみエクスポート"""
```

### データ削減基準
- **絶対保持**: 代表窓（最高R²、中央値tc、最大/最小窓）
- **条件付き保持**: R² > 0.7 または FCO条件適合
- **削除候補**: R² < 0.5 かつ 90日以上前

## 7. 📊 実装優先順位

1. **即座に実装**
   - FCOデータベーステーブル作成
   - 全窓保存ロジック
   - 基本的な読み込みAPI

2. **1ヶ月以内**
   - ダッシュボード互換層
   - データ抽出ユーティリティ

3. **3ヶ月後**
   - 使用パターン分析開始
   - 最適化戦略の検討

## 8. ⚠️ 注意事項

### データ整合性
- FOREIGN KEY制約で親子関係を保証
- CASCADE削除で孤立レコード防止

### バックアップ戦略
- 移行前に完全バックアップ
- 週次での差分バックアップ

### モニタリング
- DBサイズの定期確認
- クエリ性能の監視

## 9. 🎯 成功基準

- [ ] 全FCO分析結果が保存可能
- [ ] ダッシュボードが両形式に対応
- [ ] クエリ応答時間 < 100ms
- [ ] 年間データ増加 < 500MB
- [ ] データ抽出ツール完備

---

*このドキュメントは実装の進行に応じて更新されます*