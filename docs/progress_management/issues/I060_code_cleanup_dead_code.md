# Issue I060: Dead Code Investigation and Cleanup

## 🐛 Issue Type
Code Quality / Technical Debt

## 📅 Created
2025-08-14

## 📋 Status
Open - Investigation Required

## 🔍 Description
Issue I058の大規模ダッシュボード改修により、多くのコードが置き換えられたが、古いコードがコメントアウトされたまま残っている。これらの不要コードを調査・整理する必要がある。

## 🎯 Scope

### 1. Commented Out Code
- **LPPL Fitting Plot Tab**: 完全にコメントアウトされたタブコード
- **旧Individual Results実装**: 古い実装のコメント化されたコード
- **デバッグ用コメント**: 開発中に追加された一時的なコメント

### 2. Unused Functions
- Tab削除により使用されなくなった関数
- リファクタリングで置き換えられた古い実装
- セッション状態管理の旧バージョン

### 3. Dead Imports
- 使用されなくなったライブラリのインポート
- 重複インポート
- 開発時のテスト用インポート

## 📍 Target Files

### Primary Target
```python
applications/dashboards/main_dashboard.py  # 4400+ lines - needs cleanup
```

### Secondary Targets
```python
infrastructure/visualization/lppl_visualizer.py
infrastructure/database/results_database.py
applications/analysis_tools/crash_alert_system.py
```

## 🔬 Investigation Tasks

### Phase 1: Identification
1. **Comment Analysis**
   ```bash
   # Count commented lines
   grep -c "^[\t ]*#" main_dashboard.py
   
   # Find large comment blocks
   grep -n "^[\t ]*#.*" main_dashboard.py | awk '{print NR}' | uniq -c | sort -rn
   ```

2. **Function Usage Analysis**
   - Identify all function definitions
   - Check which functions are actually called
   - Mark unused functions for removal

3. **Import Analysis**
   ```python
   # Use ast module to analyze imports
   import ast
   # Check actual usage of imported modules
   ```

## 🧹 Cleanup Strategy

### Safe Removal Criteria
1. **Commented code > 2 weeks old**: Safe to remove
2. **Unused functions with no references**: Safe to remove
3. **Debug prints/logs**: Remove from production

### Preserve Criteria
1. **TODO comments**: Keep if still relevant
2. **Documentation comments**: Always keep
3. **Complex algorithm explanations**: Keep

### Backup Strategy
1. Create git branch before cleanup
2. Document removed code in separate file if valuable
3. Keep reference to original implementation in git history

## 📊 Expected Impact

### Benefits
- **Code readability**: Reduce file from 4400+ to ~3000 lines
- **Maintenance**: Easier to understand and modify
- **Performance**: Slightly faster parsing/loading
- **Quality**: Cleaner codebase

### Risks
- **Accidental removal**: Important code might be removed
- **Lost context**: Historical decisions might be lost
- **Reference breaks**: Other files might reference removed code

## 🔧 Implementation Plan

### Step 1: Analysis (Day 1)
```bash
# Create analysis report
python -m pylint main_dashboard.py --disable=all --enable=W0611,W0612
# W0611: unused-import
# W0612: unused-variable
```

### Step 2: Backup (Day 1)
```bash
# Create cleanup branch
git checkout -b cleanup/i060-dead-code-removal

# Archive current state
cp main_dashboard.py main_dashboard_pre_cleanup.py.bak
```

### Step 3: Cleanup (Day 2)
1. Remove identified dead code
2. Run tests after each major removal
3. Verify dashboard functionality

### Step 4: Validation (Day 2)
```bash
# Run all tests
python entry_points/main.py validate --crash 1987
./run_tests.sh

# Check dashboard
python entry_points/main.py dashboard
```

## 📈 Metrics to Track

### Before Cleanup
- File size: ~4400 lines
- Comment ratio: ~20%
- Function count: ~50
- Import count: ~30

### After Cleanup (Target)
- File size: ~3000 lines (-30%)
- Comment ratio: ~10%
- Function count: ~35
- Import count: ~20

## 🚨 Warning Signs

If any of these occur, rollback immediately:
1. Dashboard fails to load
2. Tests fail (especially 1987 validation)
3. Missing functionality reported
4. Import errors

## 📝 Notes

### Related Issues
- Issue I058: Dashboard restructuring (source of dead code)
- Issue I017: Project structure issues (broader cleanup context)

### Documentation Required
- List of removed functions with reasons
- Archive of potentially useful removed code
- Updated function dependency map

## 🏷️ Tags
#technical-debt #cleanup #code-quality #maintenance #dashboard

---
*Last Updated: 2025-08-14*