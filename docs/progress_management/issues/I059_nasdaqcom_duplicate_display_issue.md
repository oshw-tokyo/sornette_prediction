# Issue I059: NASDAQCOM Duplicate Display Investigation

## 🐛 Issue Type
Display/UI Issue

## 📅 Created
2025-08-14

## 📋 Status
Open - Investigation Required

## 🔍 Description
User報告により、NASDACOMデータがダッシュボードで重複表示されているように見える問題。

## 🔬 Initial Investigation Results

### Database Check (2025-08-14)
```python
# Database query results:
Total NASDAQCOM records: 309
No exact duplicates found
```

### Findings:
1. **データベースレベル**: 完全な重複レコードは存在しない
2. **レコード数**: NASDAQCOM で309件の分析結果が保存されている
3. **可能な原因**:
   - 同一基準日で複数の分析実行
   - 表示時のフィルタリング/ソート問題
   - UI レンダリングの問題

## 🎯 Next Steps

### 調査必要項目:
1. **ダッシュボード表示ロジック確認**
   - データ取得クエリの確認
   - フィルタリング処理の確認
   - 表示時の重複排除ロジック

2. **時系列分析**
   - 同一 analysis_basis_date での複数レコード確認
   - analysis_date と analysis_basis_date の関係性

3. **UI検証**
   - Individual Fitting Results での表示確認
   - Clustering Analysis での重複確認

## 🔧 Potential Solutions

### Option 1: Display-Level Deduplication
```python
# Display時に最新のanalysis_dateのみ表示
df.sort_values('analysis_date', ascending=False).drop_duplicates(['symbol', 'analysis_basis_date'])
```

### Option 2: Database-Level Constraint
```sql
-- UNIQUE制約追加（既存データのクリーンアップ後）
CREATE UNIQUE INDEX idx_unique_analysis 
ON analysis_results(symbol, analysis_basis_date);
```

### Option 3: Analysis-Level Prevention
- 分析実行時に既存レコードチェック
- 重複基準日での分析をスキップまたは上書き

## 📊 Impact Assessment
- **Severity**: Medium
- **User Impact**: 視覚的な混乱、分析結果の信頼性への疑問
- **Data Integrity**: データベース自体の整合性は保たれている

## 📝 Notes
- ユーザー報告: "NASDACOMのデータが複数（おそらく４つ？）記載されている"
- 実際のデータベースには重複なし → 表示層の問題の可能性が高い

## 🏷️ Tags
#bug #ui #dashboard #data-display #nasdaqcom

---
*Last Updated: 2025-08-14*